import contextlib
from copy import deepcopy
import csv
from dataclasses import asdict, replace
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
import urllib.error
import urllib.parse
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import provision_workshop
import verify_workshop
from workshop_common import (
    ARM, GRAPH, PROVIDERS, ROLES, USER_SELECT, ApiError, AzureClient, Config,
    RunStore, WorkshopError, preflight, run_path,
)


CONFIG = Config(
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222",
    "test-workshop", "eastus2", 3,
)
DOMAIN = "example.onmicrosoft.com"


class FakeCloud:
    """Stateful service fixture; no real authentication, network or Azure writes."""

    def __init__(self, config=CONFIG):
        self.config = config
        self.users = {}
        self.groups = {}
        self.roles = {}
        self.directory_roles = []
        self.members = {}
        self.providers = set(PROVIDERS)
        self.writes = []
        self.passwords = {}
        self.lose_create_response = False
        self.tenant = config.tenantId
        self.quota_actions = ["Microsoft.CognitiveServices/locations/usages/read"]

    def collection(self, url):
        parsed = urllib.parse.urlsplit(url)
        if parsed.path == "/v1.0/domains":
            return [{"id": DOMAIN, "isInitial": True, "isVerified": True}]
        if parsed.path.endswith("/locations"):
            return [{"name": "eastus2"}, {"name": "westus3"}]
        if parsed.path.endswith("/transitiveMemberOf"):
            return deepcopy(self.members.get(parsed.path.split("/")[-2], []))
        if parsed.path == "/v1.0/roleManagement/directory/roleAssignments":
            return deepcopy(self.directory_roles)
        if parsed.path.endswith("/roleAssignments"):
            if "atScope()" in parsed.query:
                return deepcopy([
                    role for role in self.roles.values()
                    if not role["properties"]["scope"].lower().startswith(
                        self.config.scope.lower() + "/"
                    )
                ])
            return deepcopy([
                role for role in self.roles.values()
                if role["properties"]["scope"].lower().startswith(self.config.scope.lower())
            ])
        raise AssertionError(f"Unimplemented fixture collection: {url}")

    def request(self, method, url, body=None):
        path = urllib.parse.unquote(urllib.parse.urlsplit(url).path)
        lower = path.lower()
        if method != "GET":
            self.writes.append((method, url, deepcopy(body)))
        if path == self.config.scope and method == "GET":
            return {"tenantId": self.tenant, "state": "Enabled"}
        if "/roledefinitions/" in lower:
            return {"properties": {"permissions": [{
                "actions": self.quota_actions, "notActions": [],
                "dataActions": [], "notDataActions": [],
            }]}}
        if method == "POST" and path.endswith("/register"):
            self.providers.add(path.split("/")[-2])
            return {}
        if method == "GET" and "/providers/" in path and "/resourceGroups/" not in path:
            provider = path.split("/")[-1]
            return {"registrationState": "Registered" if provider in self.providers else "NotRegistered"}
        if method == "POST" and path == "/v1.0/users":
            upn = body["userPrincipalName"]
            if upn in self.users:
                raise ApiError(400, "DuplicateUser", method, url)
            user = {key: None for key in USER_SELECT.split(",")}
            user.update({
                "id": str(uuid.uuid5(uuid.NAMESPACE_URL, upn)),
                **{key: deepcopy(body[key]) for key in (
                    "userPrincipalName", "userType", "accountEnabled", "onPremisesExtensionAttributes",
                )},
            })
            self.users[upn] = user
            self.passwords[upn] = body["passwordProfile"]["password"]
            if self.lose_create_response:
                self.lose_create_response = False
                raise WorkshopError("Simulated lost create response.")
            return deepcopy(user)
        if method == "GET" and path.startswith("/v1.0/users/"):
            if path.rsplit("/", 1)[-1] in self.users:
                return deepcopy(self.users[path.rsplit("/", 1)[-1]])
            raise ApiError(404, "Request_ResourceNotFound", method, url)
        if "/roleassignments/" in lower and method == "PUT":
            assignment = deepcopy(body)
            assignment["id"] = path
            assignment["properties"]["scope"] = path.rsplit("/providers/", 1)[0]
            self.roles[path.lower()] = assignment
            return deepcopy(assignment)
        if "/resourcegroups/" in lower:
            if method == "PUT":
                self.groups[lower] = {
                    "id": path, "name": path.rsplit("/", 1)[-1], **deepcopy(body),
                    "properties": {"provisioningState": "Succeeded"},
                }
            if lower in self.groups:
                return deepcopy(self.groups[lower])
            raise ApiError(404, "ResourceGroupNotFound", method, url)
        raise AssertionError(f"Unimplemented fixture request: {method} {url}")

    def add_role(self, principal, role, scope, group=False):
        assignment_id = scope + "/providers/Microsoft.Authorization/roleAssignments/" + str(uuid.uuid4())
        self.roles[assignment_id.lower()] = {
            "id": assignment_id,
            "properties": {
                "principalId": principal, "principalType": "Group" if group else "User",
                "roleDefinitionId": "/providers/Microsoft.Authorization/roleDefinitions/" + role,
                "scope": scope,
            },
        }


class WorkshopTests(unittest.TestCase):
    def setUp(self):
        self.original_cwd = Path.cwd()
        self.temporary = tempfile.TemporaryDirectory()
        os.chdir(self.temporary.name)
        self.cloud = FakeCloud()

    def tearDown(self):
        os.chdir(self.original_cwd)
        self.temporary.cleanup()

    def apply(self, cloud=None, config=CONFIG):
        with contextlib.redirect_stderr(io.StringIO()):
            return provision_workshop.provision(cloud or self.cloud, config, apply=True)

    def test_plan_is_remote_and_local_read_only(self):
        result = provision_workshop.provision(self.cloud, CONFIG)
        self.assertEqual((result["createUsers"], result["createResourceGroups"], result["createRoleAssignments"]),
                         (3, 3, 9))
        self.assertEqual(self.cloud.writes, [])
        self.assertEqual(list(Path.cwd().iterdir()), [])

    def test_fifty_participants_have_only_the_required_scoped_roles(self):
        config = replace(CONFIG, participantCount=50)
        cloud = FakeCloud(config)
        result = self.apply(cloud, config)
        self.assertEqual(result["createRoleAssignments"], 150)
        self.assertEqual((len(cloud.users), len(cloud.groups), len(cloud.roles)), (50, 50, 150))
        self.assertTrue(verify_workshop.verify(cloud, config)["passed"])
        for method, url, body in cloud.writes:
            self.assertIn(method, {"POST", "PUT"})
            if method == "POST":
                self.assertEqual(url, GRAPH + "/users")
                self.assertFalse(body["passwordProfile"]["forceChangePasswordNextSignIn"])
            elif "/roleAssignments/" not in url:
                self.assertIn("/resourceGroups/", url)
        passwords = list(cloud.passwords.values())
        self.assertEqual(len(set(passwords)), 50)
        self.assertTrue(all(len(password) >= 24 for password in passwords))

    def test_example_provisions_seventy_five_accounts_with_five_isolated_se_tests(self):
        config = Config.load(str(
            Path(__file__).resolve().parents[1] / "config" / "workshop.example.json"
        ))
        cloud = FakeCloud(config)
        plan = provision_workshop.provision(cloud, config)
        self.assertEqual(
            (plan["createUsers"], plan["createResourceGroups"], plan["createRoleAssignments"]),
            (75, 75, 225),
        )
        self.assertEqual(cloud.writes, [])
        self.assertEqual(list(Path.cwd().iterdir()), [])
        participants = config.participants(DOMAIN)
        se_tests = participants[70:]
        self.assertEqual(
            [row["upn"] for row in plan["participants"][:70]],
            [f"user{i:02d}@{DOMAIN}" for i in range(1, 71)],
        )
        self.assertEqual(
            [row["resourceGroup"] for row in plan["participants"][:70]],
            [f"rg-user{i:02d}" for i in range(1, 71)],
        )
        self.assertEqual(
            [p.alias for p in se_tests],
            [f"se{i:02d}" for i in range(1, 6)],
        )
        self.assertEqual(
            [row["resourceGroup"] for row in plan["participants"][70:]],
            [f"rg-se{i:02d}" for i in range(1, 6)],
        )
        self.assertEqual(
            sum(row["accountPurpose"] == "se-test" for row in plan["participants"]), 5,
        )
        result = self.apply(cloud, config)
        self.assertEqual((len(cloud.users), len(cloud.groups), len(cloud.roles)), (75, 75, 225))
        verification = verify_workshop.verify(cloud, config)
        self.assertTrue(verification["passed"])
        self.assertEqual(len(verification["participants"]), 75)
        credential_path = run_path(config) / "credentials.private.csv"
        credentials = credential_path.read_bytes()
        with credential_path.open(newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 75)
        self.assertEqual(sum(row["accountPurpose"] == "participant" for row in rows), 70)
        self.assertEqual(
            {row["userPrincipalName"] for row in rows if row["accountPurpose"] == "se-test"},
            {p.upn for p in se_tests},
        )
        public_output = json.dumps((plan, result, verification))
        for password in cloud.passwords.values():
            self.assertNotIn(password, public_output)
        cloud.writes.clear()
        self.apply(cloud, config)
        self.assertEqual(cloud.writes, [])
        self.assertEqual(credential_path.read_bytes(), credentials)
        with self.assertRaises(WorkshopError):
            self.apply(cloud, replace(config, workshopId="another-workshop"))
        self.assertEqual(cloud.writes, [])
        se_test = se_tests[-1]
        tags = cloud.groups[se_test.scope.lower()]["tags"]
        self.assertEqual(tags.pop("accountPurpose"), "se-test")
        self.assertFalse(verify_workshop.verify(cloud, config)["passed"])
        tags["accountPurpose"] = "se-test"
        cloud.add_role(cloud.users[se_test.upn]["id"], ROLES["Contributor"], participants[0].scope)
        self.assertFalse(verify_workshop.verify(cloud, config)["passed"])

    def test_legacy_five_key_config_and_journal_rerun_without_changes(self):
        legacy = asdict(CONFIG)
        del legacy["seTestAccountCount"]
        del legacy["namePrefix"]
        del legacy["nameFormat"]
        Path("config.json").write_text(json.dumps(legacy))
        config = Config.load("config.json")
        self.assertEqual(config, CONFIG)
        self.apply(config=config)
        state_path = run_path(config) / "state.private.json"
        state = json.loads(state_path.read_text())
        legacy_binding = hashlib.sha256(
            json.dumps({"config": legacy, "domain": DOMAIN}, sort_keys=True).encode()
        ).hexdigest()
        self.assertEqual(state["binding"], legacy_binding)
        for saved in state["participants"].values():
            del saved["accountPurpose"]
        state_path.write_text(json.dumps(state))
        credentials = (run_path(config) / "credentials.private.csv").read_bytes()
        self.cloud.writes.clear()
        self.apply(config=config)
        self.assertEqual(self.cloud.writes, [])
        self.assertEqual((run_path(config) / "credentials.private.csv").read_bytes(), credentials)
        self.assertTrue(verify_workshop.verify(self.cloud, config)["passed"])

    def test_legacy_six_key_se_config_keeps_names_and_journal(self):
        config = replace(CONFIG, seTestAccountCount=1)
        cloud = FakeCloud(config)
        legacy = asdict(config)
        del legacy["namePrefix"]
        del legacy["nameFormat"]
        Path("config.json").write_text(json.dumps(legacy))
        config = Config.load("config.json")
        result = self.apply(cloud, config)
        self.assertEqual(result["participants"][0]["upn"], f"test-workshop-001@{DOMAIN}")
        self.assertEqual(result["participants"][-1]["upn"], f"test-workshop-se-test-001@{DOMAIN}")
        self.assertEqual(result["participants"][-1]["resourceGroup"], "rg-test-workshop-se-test-001")
        state = json.loads((run_path(config) / "state.private.json").read_text())
        legacy_binding = hashlib.sha256(
            json.dumps({"config": legacy, "domain": DOMAIN}, sort_keys=True).encode()
        ).hexdigest()
        self.assertEqual(state["binding"], legacy_binding)
        credentials = (run_path(config) / "credentials.private.csv").read_bytes()
        cloud.writes.clear()
        self.apply(cloud, config)
        self.assertEqual(cloud.writes, [])
        self.assertEqual((run_path(config) / "credentials.private.csv").read_bytes(), credentials)
        self.assertTrue(verify_workshop.verify(cloud, config)["passed"])

    def test_legacy_seven_key_compact_config_keeps_names_and_journal(self):
        config = replace(CONFIG, seTestAccountCount=1, namePrefix="w")
        cloud = FakeCloud(config)
        legacy = asdict(config)
        del legacy["nameFormat"]
        Path("config.json").write_text(json.dumps(legacy))
        config = Config.load("config.json")
        result = self.apply(cloud, config)
        self.assertEqual(result["participants"][0]["upn"], f"w1@{DOMAIN}")
        self.assertEqual(result["participants"][0]["resourceGroup"], "w1")
        self.assertEqual(result["participants"][-1]["upn"], f"ws1@{DOMAIN}")
        self.assertEqual(result["participants"][-1]["resourceGroup"], "ws1")
        state = json.loads((run_path(config) / "state.private.json").read_text())
        legacy_binding = hashlib.sha256(
            json.dumps({"config": legacy, "domain": DOMAIN}, sort_keys=True).encode()
        ).hexdigest()
        self.assertEqual(state["binding"], legacy_binding)
        credentials = (run_path(config) / "credentials.private.csv").read_bytes()
        cloud.writes.clear()
        self.apply(cloud, config)
        self.assertEqual(cloud.writes, [])
        self.assertEqual((run_path(config) / "credentials.private.csv").read_bytes(), credentials)
        self.assertTrue(verify_workshop.verify(cloud, config)["passed"])
        for prefix in ("w", "ws"):
            with self.subTest(colliding_prefix=prefix):
                with self.assertRaises(WorkshopError):
                    self.apply(cloud, replace(
                        config, workshopId="another-workshop", namePrefix=prefix,
                    ))
                self.assertEqual(cloud.writes, [])

    def test_rerun_does_not_create_reset_or_duplicate(self):
        self.apply()
        credentials = (run_path(CONFIG) / "credentials.private.csv").read_bytes()
        self.cloud.writes.clear()
        result = self.apply()
        self.assertEqual(self.cloud.writes, [])
        self.assertEqual(result["createRoleAssignments"], 0)
        self.assertEqual((run_path(CONFIG) / "credentials.private.csv").read_bytes(), credentials)

    def test_rerun_repairs_only_a_missing_role(self):
        self.apply()
        self.cloud.roles.pop(next(iter(self.cloud.roles)))
        self.cloud.writes.clear()
        self.apply()
        self.assertEqual(len(self.cloud.writes), 1)
        self.assertIn("/roleAssignments/", self.cloud.writes[0][1])
        self.assertTrue(verify_workshop.verify(self.cloud, CONFIG)["passed"])

    def test_lost_create_response_uses_the_precommitted_password(self):
        self.cloud.lose_create_response = True
        with self.assertRaisesRegex(WorkshopError, "lost create response"):
            self.apply()
        state_path = run_path(CONFIG) / "state.private.json"
        state = json.loads(state_path.read_text())
        first = state["participants"]["001"]
        self.assertNotIn("objectId", first)
        self.assertEqual(first["initialPassword"], self.cloud.passwords[first["upn"]])
        self.apply()
        state = json.loads(state_path.read_text())
        self.assertEqual(state["participants"]["001"]["initialPassword"], first["initialPassword"])
        self.assertEqual(sum(method == "POST" for method, _, _ in self.cloud.writes), 3)
        self.assertTrue(verify_workshop.verify(self.cloud, CONFIG)["passed"])

    def test_collision_at_last_participant_prevents_all_remote_writes(self):
        config = replace(CONFIG, participantCount=75, seTestAccountCount=5, nameFormat="user-se")
        for collision in ("user", "group"):
            with self.subTest(collision=collision):
                cloud = FakeCloud(config)
                participant = config.participants(DOMAIN)[-1]
                if collision == "user":
                    cloud.users[participant.upn] = {
                        "id": str(uuid.uuid4()), "userPrincipalName": participant.upn,
                    }
                else:
                    cloud.groups[participant.scope.lower()] = {
                        "id": participant.scope, "name": participant.rg, "location": "eastus2",
                        "properties": {"provisioningState": "Succeeded"}, "tags": {},
                    }
                with self.assertRaises(WorkshopError):
                    self.apply(cloud, config)
                self.assertEqual(cloud.writes, [])

    def test_wrong_tenant_or_location_prevents_writes(self):
        self.cloud.tenant = str(uuid.uuid4())
        with self.assertRaisesRegex(WorkshopError, "tenant"):
            self.apply()
        self.assertEqual(self.cloud.writes, [])
        self.cloud.tenant = CONFIG.tenantId
        with self.assertRaisesRegex(WorkshopError, "location"):
            self.apply(config=replace(CONFIG, location="notarealregion"))
        self.assertEqual(self.cloud.writes, [])

    def test_provider_registration_is_apply_only_and_then_verified(self):
        self.cloud.providers.remove(PROVIDERS[-1])
        plan = provision_workshop.provision(self.cloud, CONFIG)
        self.assertEqual(plan["registerProviders"], [PROVIDERS[-1]])
        self.assertEqual(self.cloud.writes, [])
        self.apply()
        self.assertEqual(self.cloud.writes[0][0], "POST")
        self.assertIn("/register?", self.cloud.writes[0][1])
        self.assertTrue(verify_workshop.verify(self.cloud, CONFIG)["passed"])
        self.cloud.providers.remove(PROVIDERS[-1])
        self.assertFalse(verify_workshop.verify(self.cloud, CONFIG)["passed"])

    def test_quota_reader_cannot_gain_resource_group_listing(self):
        self.cloud.quota_actions.append("Microsoft.Resources/subscriptions/resourceGroups/read")
        with self.assertRaisesRegex(WorkshopError, "Quota-reader permissions changed"):
            self.apply()
        self.assertEqual(self.cloud.writes, [])

    def test_independent_verification_does_not_trust_or_need_the_journal(self):
        self.apply()
        (run_path(CONFIG) / "state.private.json").unlink()
        self.assertTrue(verify_workshop.verify(self.cloud, CONFIG)["passed"])
        self.cloud.users[next(iter(self.cloud.users))]["accountEnabled"] = False
        self.assertFalse(verify_workshop.verify(self.cloud, CONFIG)["passed"])
        self.cloud.writes.clear()
        with self.assertRaises(WorkshopError):
            self.apply()
        self.assertEqual(self.cloud.writes, [])

    def test_verifier_finds_missing_or_incorrect_identity_rg_and_role(self):
        self.apply()
        clean_users, clean_groups, clean_roles = deepcopy(
            (self.cloud.users, self.cloud.groups, self.cloud.roles)
        )
        participant = CONFIG.participants(DOMAIN)[0]
        for defect in ("user", "member", "disabled", "identity-shape", "marker", "rg",
                       "tag", "region", "role", "role-scope", "role-condition"):
            with self.subTest(defect=defect):
                self.cloud.users, self.cloud.groups, self.cloud.roles = deepcopy(
                    (clean_users, clean_groups, clean_roles)
                )
                user = self.cloud.users[participant.upn]
                group = self.cloud.groups[participant.scope.lower()]
                assignment = next(
                    role["properties"] for role in self.cloud.roles.values()
                    if role["properties"]["scope"].lower() == participant.scope.lower()
                )
                if defect == "user":
                    del self.cloud.users[participant.upn]
                elif defect == "member":
                    user["userType"] = "Member"
                elif defect == "disabled":
                    user["accountEnabled"] = False
                elif defect == "identity-shape":
                    del user["creationType"]
                elif defect == "marker":
                    user["onPremisesExtensionAttributes"] = {}
                elif defect == "rg":
                    del self.cloud.groups[participant.scope.lower()]
                elif defect == "tag":
                    group["tags"]["participantId"] = "someone-else"
                elif defect == "region":
                    group["location"] = "westus3"
                elif defect == "role":
                    self.cloud.roles.pop(next(iter(self.cloud.roles)))
                elif defect == "role-scope":
                    assignment["scope"] = CONFIG.scope
                else:
                    assignment["condition"] = "conditional"
                result = verify_workshop.verify(self.cloud, CONFIG)
                self.assertFalse(result["passed"])
                self.assertTrue(result["participants"][0]["issues"])

    def test_other_rg_subscription_parent_and_resource_roles_are_rejected(self):
        self.apply()
        baseline = deepcopy(self.cloud.roles)
        user = next(iter(self.cloud.users.values()))
        scopes = [
            CONFIG.scope + "/resourceGroups/rg-other-customer",
            CONFIG.scope,
            "/providers/Microsoft.Management/managementGroups/parent",
            "/",
            CONFIG.participants(DOMAIN)[0].scope + "/providers/Microsoft.Storage/storageAccounts/shared",
        ]
        for scope in scopes:
            with self.subTest(scope=scope):
                self.cloud.roles = deepcopy(baseline)
                self.cloud.add_role(user["id"], ROLES["Contributor"], scope)
                self.assertFalse(verify_workshop.verify(self.cloud, CONFIG)["passed"])
                self.cloud.writes.clear()
                with self.assertRaisesRegex(WorkshopError, "Unexpected"):
                    self.apply()
                self.assertEqual(self.cloud.writes, [])

    def test_transitive_group_permissions_and_scoped_entra_roles_are_rejected(self):
        self.apply()
        baseline = deepcopy(self.cloud.roles)
        user = next(iter(self.cloud.users.values()))
        group_id = str(uuid.uuid4())
        self.cloud.members[user["id"]] = [{
            "id": group_id, "@odata.type": "#microsoft.graph.group",
        }]
        self.cloud.add_role(group_id, ROLES["Contributor"], CONFIG.scope, group=True)
        self.assertFalse(verify_workshop.verify(self.cloud, CONFIG)["passed"])
        self.cloud.roles = baseline
        self.assertTrue(verify_workshop.verify(self.cloud, CONFIG)["passed"])
        for principal in (user["id"], group_id):
            self.cloud.directory_roles = [{
                "id": str(uuid.uuid4()), "principalId": principal,
                "roleDefinitionId": str(uuid.uuid4()),
                "directoryScopeId": "/administrativeUnits/" + str(uuid.uuid4()),
            }]
            self.assertFalse(verify_workshop.verify(self.cloud, CONFIG)["passed"])

    def test_private_output_modes_locks_and_symlinks(self):
        self.apply()
        folder = run_path(CONFIG)
        self.assertEqual(folder.stat().st_mode & 0o777, 0o700)
        for path in folder.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        with RunStore(CONFIG):
            with self.assertRaises(WorkshopError):
                with RunStore(CONFIG):
                    self.fail("Concurrent lock should have failed")
        credentials = folder / "credentials.private.csv"
        credentials.unlink()
        outside = Path("outside.txt")
        outside.write_text("unchanged")
        credentials.symlink_to(outside.resolve())
        with self.assertRaises(WorkshopError):
            self.apply()
        self.assertEqual(outside.read_text(), "unchanged")

    def test_config_change_and_world_readable_journal_are_not_adopted(self):
        self.apply()
        for changed in (
            replace(CONFIG, participantCount=4),
            replace(CONFIG, seTestAccountCount=1),
            replace(CONFIG, namePrefix="w"),
            replace(CONFIG, nameFormat="user-se"),
        ):
            self.cloud.writes.clear()
            with self.assertRaisesRegex(WorkshopError, "state/config mismatch"):
                self.apply(config=changed)
            self.assertEqual(self.cloud.writes, [])
        state = run_path(CONFIG) / "state.private.json"
        state.chmod(0o644)
        self.cloud.writes.clear()
        with self.assertRaisesRegex(WorkshopError, "Private path"):
            self.apply()
        self.assertEqual(self.cloud.writes, [])

    def test_verifier_cli_fails_closed_and_replaces_stale_pass_report(self):
        self.apply()
        Path("config.json").write_text(json.dumps(asdict(CONFIG)))
        output, error = io.StringIO(), io.StringIO()
        with patch.object(verify_workshop, "AzureClient", return_value=self.cloud):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
                self.assertEqual(verify_workshop.main(["--config", "config.json"]), 0)
                original = self.cloud.collection

                def forbidden(url):
                    if "roleAssignments" in url:
                        raise ApiError(403, "AuthorizationFailed", "GET", url)
                    return original(url)

                self.cloud.collection = forbidden
                self.assertEqual(verify_workshop.main(["--config", "config.json"]), 1)
        report = json.loads((run_path(CONFIG) / "verification.private.json").read_text())
        self.assertFalse(report["passed"])
        self.assertEqual(report["status"], "error")
        self.assertIn("audit incomplete", error.getvalue())

    def test_invalid_config_is_rejected(self):
        data = asdict(CONFIG)
        for key, value in (
            ("tenantId", "not-a-uuid"), ("workshopId", "../../outside"),
            ("workshopId", "UpperCase"), ("participantCount", True),
            ("participantCount", 0), ("participantCount", 1000),
            ("seTestAccountCount", True), ("seTestAccountCount", -1),
            ("seTestAccountCount", 4), ("seTestAccountCount", 1.5),
            ("namePrefix", ""), ("namePrefix", "W"), ("namePrefix", "../w"),
            ("namePrefix", "w-"), ("namePrefix", "1w"), ("namePrefix", True),
            ("namePrefix", "w" * 33),
            ("nameFormat", "unknown"), ("nameFormat", True),
            ("location", "East US 2"), ("unknown", "do-not-log-this"),
        ):
            with self.subTest(key=key, value=value):
                invalid = {**data, key: value}
                Path("config.json").write_text(json.dumps(invalid))
                with self.assertRaises(WorkshopError):
                    Config.load("config.json")
        Path("config.json").write_text(json.dumps({
            **data, "namePrefix": "w", "nameFormat": "user-se",
        }))
        with self.assertRaisesRegex(WorkshopError, "not both"):
            Config.load("config.json")


class HttpTests(unittest.TestCase):
    def client(self):
        with patch("workshop_common.cli_json", return_value={
            "id": CONFIG.subscriptionId, "tenantId": CONFIG.tenantId,
            "environmentName": "AzureCloud", "state": "Enabled",
        }):
            client = AzureClient(CONFIG)
        client.token = Mock(return_value="never-print-this-token")
        client.opener = Mock()
        return client

    def test_retry_after_is_honored_for_safe_requests(self):
        client = self.client()
        client.opener.open.side_effect = [
            urllib.error.HTTPError(ARM + CONFIG.scope, 429, "busy", {"Retry-After": "2"},
                                   io.BytesIO(b'{"error":{"code":"TooManyRequests"}}')),
            io.BytesIO(b'{"value":[]}'),
        ]
        with patch("workshop_common.time.sleep") as sleep:
            self.assertEqual(client.request("GET", ARM + CONFIG.scope), {"value": []})
        sleep.assert_called_once_with(2)
        self.assertEqual(client.opener.open.call_count, 2)

    def test_password_bearing_post_is_not_retried_or_disclosed(self):
        client = self.client()
        secret = "never-print-the-password"
        client.opener.open.side_effect = urllib.error.HTTPError(
            GRAPH + "/users", 503, "failed", {},
            io.BytesIO(json.dumps({"error": {"code": "Unavailable", "message": secret}}).encode()),
        )
        with self.assertRaises(ApiError) as caught:
            client.request("POST", GRAPH + "/users", {"passwordProfile": {"password": secret}})
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn("never-print-this-token", str(caught.exception))
        self.assertEqual(client.opener.open.call_count, 1)

    def test_all_pagination_pages_are_read_and_untrusted_next_links_refused(self):
        client = self.client()
        initial = GRAPH + "/domains"
        second = initial + "?skiptoken=next"
        client.request = Mock(side_effect=[
            {"value": [{"id": "one"}], "@odata.nextLink": second},
            {"value": [{"id": "two"}]},
        ])
        self.assertEqual(client.collection(initial), [{"id": "one"}, {"id": "two"}])
        for bad in (
            "https://evil.example/steal-token",
            ARM + CONFIG.scope + "/providers/anything",
            initial,
        ):
            client.request = Mock(return_value={"value": [], "@odata.nextLink": bad})
            with self.assertRaises(WorkshopError):
                client.collection(initial)
        with self.assertRaises(WorkshopError):
            client.validate_url(ARM + "/subscriptions/" + str(uuid.uuid4()) + "/resources")

    def test_wrong_cli_tenant_and_http_forbidden_are_not_success(self):
        with patch("workshop_common.cli_json", return_value={
            "id": CONFIG.subscriptionId, "tenantId": str(uuid.uuid4()),
            "environmentName": "AzureCloud", "state": "Enabled",
        }):
            with self.assertRaisesRegex(WorkshopError, "does not match"):
                AzureClient(CONFIG)
        client = self.client()
        client.opener.open.side_effect = urllib.error.HTTPError(
            GRAPH + "/users", 403, "forbidden", {},
            io.BytesIO(b'{"error":{"code":"Authorization_RequestDenied"}}'),
        )
        with self.assertRaisesRegex(ApiError, "403"):
            client.request("GET", GRAPH + "/users")
        self.assertEqual(client.opener.open.call_count, 1)

    def test_transport_failure_does_not_echo_secret_and_redirects_are_disabled(self):
        client = self.client()
        client.opener.open.side_effect = urllib.error.URLError("secret-password-in-error")
        with self.assertRaises(WorkshopError) as caught:
            client.request("POST", GRAPH + "/users", {"password": "secret-password"})
        self.assertNotIn("secret-password", str(caught.exception))
        from workshop_common import NoRedirect
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.example"))


if __name__ == "__main__":
    unittest.main()
