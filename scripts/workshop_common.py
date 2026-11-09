"""Shared configuration, API reads and private output for the workshop tools."""

import csv
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


GRAPH = "https://graph.microsoft.com/v1.0"
ARM = "https://management.azure.com"
AUTH_API = "2022-04-01"
RG_API = "2021-04-01"
ROLES = {
    "Contributor": "b24988ac-6180-42a0-ab88-20f7382dd24c",
    "Foundry User": "53ca6127-db72-4b80-b1b0-d745d6d5456d",
    "Cognitive Services Usages Reader": "bba48692-92b0-4667-a9ad-c31c7b334ac2",
}
PROVIDERS = (
    "Microsoft.CognitiveServices", "Microsoft.OperationalInsights",
    "Microsoft.Insights", "Microsoft.Storage", "Microsoft.Search",
    "Microsoft.ManagedIdentity", "Microsoft.KeyVault", "Microsoft.DocumentDB",
)
USER_SELECT = (
    "id,userPrincipalName,userType,accountEnabled,creationType,externalUserState,"
    "onPremisesSyncEnabled,onPremisesExtensionAttributes"
)


class WorkshopError(Exception):
    pass


class ApiError(WorkshopError):
    def __init__(self, status: int, code: str, method: str, url: str):
        self.status = status
        path = urllib.parse.urlsplit(url).path
        super().__init__(f"{method} {path}: HTTP {status} ({code}).")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Config:
    tenantId: str
    subscriptionId: str
    workshopId: str
    location: str
    participantCount: int
    seTestAccountCount: int = 0
    namePrefix: str | None = None
    nameFormat: str | None = None

    @classmethod
    def load(cls, path: str) -> "Config":
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise WorkshopError("Cannot read the JSON config file.") from exc
        required = set(cls.__annotations__) - {"seTestAccountCount", "namePrefix", "nameFormat"}
        if (
            not isinstance(data, dict) or not required <= set(data)
            or set(data) - set(cls.__annotations__)
        ):
            raise WorkshopError(
                "Config needs the five required keys and optional seTestAccountCount/namePrefix/nameFormat."
            )
        data.setdefault("seTestAccountCount", 0)
        data.setdefault("namePrefix", None)
        data.setdefault("nameFormat", None)
        for key in ("tenantId", "subscriptionId"):
            try:
                data[key] = str(uuid.UUID(data[key]))
            except (ValueError, TypeError, AttributeError) as exc:
                raise WorkshopError(f"{key} must be a UUID.") from exc
        name = data["workshopId"]
        if not isinstance(name, str) or not re.fullmatch(
            r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", name
        ) or not 3 <= len(name) <= 32:
            raise WorkshopError("workshopId must be 3-32 lowercase letters/digits/hyphens.")
        if not isinstance(data["location"], str) or not re.fullmatch(
            r"[a-z][a-z0-9]{1,39}", data["location"]
        ):
            raise WorkshopError("Use an Azure location name such as eastus2.")
        count = data["participantCount"]
        if type(count) is not int or not 1 <= count <= 999:
            raise WorkshopError("participantCount must be an integer from 1 to 999.")
        se_count = data["seTestAccountCount"]
        if type(se_count) is not int or not 0 <= se_count <= count:
            raise WorkshopError("seTestAccountCount must be an integer from 0 to participantCount.")
        prefix = data["namePrefix"]
        if prefix is not None and (
            not isinstance(prefix, str) or not re.fullmatch(r"[a-z][a-z0-9]{0,31}", prefix)
        ):
            raise WorkshopError(
                "namePrefix must be 1-32 lowercase letters/digits, starting with a letter."
            )
        name_format = data["nameFormat"]
        if name_format is not None and name_format != "user-se":
            raise WorkshopError("nameFormat must be 'user-se' or omitted.")
        if name_format is not None and prefix is not None:
            raise WorkshopError("Use nameFormat or the older namePrefix setting, not both.")
        return cls(**data)

    @property
    def scope(self) -> str:
        return f"/subscriptions/{self.subscriptionId}"

    @property
    def marker(self) -> str:
        return f"foundry-workshop:{self.subscriptionId}:{self.workshopId}"

    def participants(self, domain: str) -> list["Participant"]:
        return [
            Participant(self, f"{i:03d}", domain)
            for i in range(1, self.participantCount + 1)
        ]


@dataclass(frozen=True)
class Participant:
    config: Config
    number: str
    domain: str

    @property
    def account_purpose(self) -> str:
        return (
            "se-test"
            if int(self.number) > self.config.participantCount - self.config.seTestAccountCount
            else "participant"
        )

    @property
    def alias(self) -> str:
        if self.account_purpose == "se-test":
            number = int(self.number) - self.config.participantCount + self.config.seTestAccountCount
            if self.config.nameFormat == "user-se":
                return f"se{number:02d}"
            if self.config.namePrefix is not None:
                return f"{self.config.namePrefix}s{number}"
            return f"{self.config.workshopId}-se-test-{number:03d}"
        if self.config.nameFormat == "user-se":
            return f"user{int(self.number):02d}"
        if self.config.namePrefix is not None:
            return f"{self.config.namePrefix}{int(self.number)}"
        return f"{self.config.workshopId}-{self.number}"

    @property
    def upn(self) -> str:
        return f"{self.alias}@{self.domain}"

    @property
    def rg(self) -> str:
        if self.config.namePrefix is not None and self.config.nameFormat is None:
            return self.alias
        return f"rg-{self.alias}"

    @property
    def scope(self) -> str:
        return f"{self.config.scope}/resourceGroups/{self.rg}"

    @property
    def tags(self) -> dict[str, str]:
        tags = {
            "managedBy": "foundry-workshop-script",
            "workshopId": self.config.workshopId,
            "participantId": self.number,
        }
        if self.account_purpose == "se-test":
            tags["accountPurpose"] = "se-test"
        return tags

    @property
    def expected_roles(self) -> set[tuple[str, str]]:
        return {
            (self.scope.lower(), ROLES["Contributor"]),
            (self.scope.lower(), ROLES["Foundry User"]),
            (self.config.scope.lower(), ROLES["Cognitive Services Usages Reader"]),
        }


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def cli_json(arguments: list[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["az", *arguments, "--only-show-errors", "--output", "json"],
            capture_output=True, text=True, timeout=90, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise WorkshopError("Cannot run Azure CLI. Check az installation/login.") from exc
    if result.returncode:
        raise WorkshopError(
            "Azure CLI authentication failed. Run az login --tenant <tenantId> "
            "with an approved SE account; CLI stderr is not logged."
        )
    try:
        data = json.loads(result.stdout)
    except ValueError as exc:
        raise WorkshopError("Azure CLI did not return valid JSON.") from exc
    if not isinstance(data, dict):
        raise WorkshopError("Unexpected Azure CLI response.")
    return data


class AzureClient:
    def __init__(self, config: Config):
        self.config = config
        account = cli_json(["account", "show", "--subscription", config.subscriptionId])
        if (
            account.get("id", "").lower() != config.subscriptionId
            or account.get("tenantId", "").lower() != config.tenantId
            or account.get("environmentName") != "AzureCloud"
            or account.get("state") != "Enabled"
        ):
            raise WorkshopError("Subscription/tenant/cloud/state does not match the config.")
        self.tokens: dict[str, tuple[str, int]] = {}
        self.opener = urllib.request.build_opener(NoRedirect())

    def validate_url(self, url: str) -> str:
        parsed = urllib.parse.urlsplit(url)
        graph = parsed.netloc == "graph.microsoft.com" and parsed.path.startswith("/v1.0/")
        arm = parsed.netloc == "management.azure.com" and (
            parsed.path.lower() == self.config.scope
            or parsed.path.lower().startswith(self.config.scope + "/")
        )
        if (
            parsed.scheme != "https" or parsed.fragment
            or parsed.username or parsed.password or not (graph or arm)
        ):
            raise WorkshopError("Refusing an API URL outside the configured cloud/scope.")
        return f"{parsed.scheme}://{parsed.netloc}"

    def token(self, origin: str) -> str:
        cached = self.tokens.get(origin)
        if cached and cached[1] > time.time() + 300:
            return cached[0]
        data = cli_json([
            "account", "get-access-token", "--subscription", self.config.subscriptionId,
            "--resource", origin + "/",
        ])
        if data.get("tenant", "").lower() != self.config.tenantId:
            raise WorkshopError("Azure CLI returned a token for the wrong tenant.")
        if not isinstance(data.get("accessToken"), str) or not data["accessToken"]:
            raise WorkshopError("Azure CLI returned no access token.")
        try:
            expires = int(data["expires_on"])
        except (KeyError, ValueError, TypeError) as exc:
            raise WorkshopError("Azure CLI token has no expires_on; update Azure CLI.") from exc
        self.tokens[origin] = (data["accessToken"], expires)
        return data["accessToken"]

    def request(
        self, method: str, url: str, body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        origin = self.validate_url(url)
        payload = None if body is None else json.dumps(body).encode("utf-8")
        for attempt in range(5):
            request = urllib.request.Request(
                url, data=payload, method=method,
                headers={
                    "Authorization": "Bearer " + self.token(origin),
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            try:
                with self.opener.open(request, timeout=60) as response:
                    raw = response.read()
                data = json.loads(raw) if raw else {}
                if not isinstance(data, dict):
                    raise WorkshopError("API response is not a JSON object.")
                return data
            except urllib.error.HTTPError as exc:
                if (
                    method in {"GET", "PUT"} and attempt < 4
                    and exc.code in {408, 429, 500, 502, 503, 504}
                ):
                    retry = exc.headers.get("Retry-After")
                    try:
                        delay = float(retry) if retry else 2 ** attempt
                    except ValueError:
                        try:
                            delay = parsedate_to_datetime(retry).timestamp() - time.time()
                        except (TypeError, ValueError, OverflowError) as date_exc:
                            raise WorkshopError("Invalid API Retry-After header.") from date_exc
                    exc.close()
                    if not 0 <= delay <= 300:
                        raise WorkshopError("Retry-After exceeds 300s; retry the command later.")
                    time.sleep(delay)
                    continue
                try:
                    error = json.loads(exc.read()).get("error", {})
                    code = error.get("code", "UnknownApiError")
                except (ValueError, AttributeError):
                    code = "UnknownApiError"
                finally:
                    exc.close()
                if not isinstance(code, str) or not re.fullmatch(r"[\w.-]{1,100}", code):
                    code = "UnknownApiError"
                raise ApiError(exc.code, code, method, url) from None
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                raise WorkshopError(
                    f"{method} API transport failed ({type(exc).__name__}); "
                    "no POST retry was attempted. Rerun with the same private state."
                ) from None
            except ValueError as exc:
                raise WorkshopError("API returned invalid JSON; rerun with the same state.") from exc
        raise WorkshopError("API retry limit exceeded.")

    def collection(self, url: str) -> list[dict[str, Any]]:
        origin = self.validate_url(url)
        result = []
        seen = set()
        while url:
            if url in seen or self.validate_url(url) != origin:
                raise WorkshopError("Invalid or cyclic API pagination link.")
            seen.add(url)
            data = self.request("GET", url)
            if not isinstance(data.get("value"), list):
                raise WorkshopError("API collection has no value array.")
            if not all(isinstance(item, dict) for item in data["value"]):
                raise WorkshopError("API collection contains a non-object item.")
            result.extend(data["value"])
            url = data.get("@odata.nextLink") or data.get("nextLink")
            if url is not None and not isinstance(url, str):
                raise WorkshopError("Invalid API pagination link type.")
        return result


def api_url(path: str, version: str) -> str:
    return f"{ARM}{path}?api-version={version}"


def get_optional(client: AzureClient, url: str) -> dict[str, Any] | None:
    try:
        return client.request("GET", url)
    except ApiError as exc:
        if exc.status == 404:
            return None
        raise


def get_user(client: AzureClient, participant: Participant) -> dict[str, Any] | None:
    upn = urllib.parse.quote(participant.upn, safe="")
    return get_optional(client, f"{GRAPH}/users/{upn}?$select={USER_SELECT}")


def get_rg(client: AzureClient, participant: Participant) -> dict[str, Any] | None:
    return get_optional(client, api_url(participant.scope, RG_API))


def preflight(client: AzureClient, config: Config) -> tuple[str, list[str]]:
    subscription = client.request("GET", api_url(config.scope, "2022-12-01"))
    if (
        subscription.get("tenantId", "").lower() != config.tenantId
        or subscription.get("state") != "Enabled"
    ):
        raise WorkshopError("ARM subscription tenant/state does not match the config.")
    domains = client.collection(f"{GRAPH}/domains?$select=id,isInitial,isVerified")
    initial = [
        domain["id"].lower() for domain in domains
        if domain.get("isInitial") is True and domain.get("isVerified") is True
        and isinstance(domain.get("id"), str)
        and re.fullmatch(r"[a-z0-9-]+\.onmicrosoft\.com", domain["id"], re.I)
    ]
    if len(initial) != 1:
        raise WorkshopError("Expected one verified initial onmicrosoft.com domain.")
    locations = client.collection(api_url(config.scope + "/locations", "2022-12-01"))
    if config.location not in {item.get("name", "").lower() for item in locations}:
        raise WorkshopError("Configured Azure location is not available in this subscription.")
    for role in ROLES.values():
        definition = client.request("GET", api_url(
            config.scope + "/providers/Microsoft.Authorization/roleDefinitions/" + role,
            AUTH_API,
        ))
        if role == ROLES["Cognitive Services Usages Reader"]:
            permissions = definition.get("properties", {}).get("permissions")
            if not isinstance(permissions, list) or not permissions:
                raise WorkshopError("Cannot inspect the subscription quota-reader permissions.")
            actions = {
                action.lower() for permission in permissions
                for action in permission.get("actions", [])
            }
            if actions != {"microsoft.cognitiveservices/locations/usages/read"} or any(
                permission.get(key) for permission in permissions
                for key in ("notActions", "dataActions", "notDataActions")
            ):
                raise WorkshopError("Quota-reader permissions changed; review RG isolation first.")
    missing_providers = []
    for provider in PROVIDERS:
        data = client.request("GET", api_url(
            config.scope + "/providers/" + provider, "2021-04-01"
        ))
        if data.get("registrationState") != "Registered":
            missing_providers.append(provider)
    return initial[0], missing_providers


def role_snapshot(client: AzureClient, config: Config) -> list[dict[str, Any]]:
    url = api_url(config.scope + "/providers/Microsoft.Authorization/roleAssignments", AUTH_API)
    assignments = client.collection(url) + client.collection(url + "&$filter=atScope()")
    by_id = {}
    for assignment in assignments:
        properties = assignment.get("properties")
        if (
            not isinstance(assignment.get("id"), str)
            or not isinstance(properties, dict)
            or any(not isinstance(properties.get(key), str) or not properties[key]
                   for key in ("principalId", "scope", "roleDefinitionId"))
        ):
            raise WorkshopError("Incomplete Azure role assignment; cannot audit access.")
        by_id[assignment["id"].lower()] = assignment
    return list(by_id.values())


def directory_snapshot(client: AzureClient) -> list[dict[str, Any]]:
    assignments = client.collection(
        f"{GRAPH}/roleManagement/directory/roleAssignments"
        "?$select=id,principalId,roleDefinitionId,directoryScopeId"
    )
    if any(not item.get("principalId") or not item.get("roleDefinitionId") for item in assignments):
        raise WorkshopError("Incomplete active Entra role assignments; cannot audit access.")
    return assignments


def user_issues(user: dict[str, Any], participant: Participant) -> list[str]:
    issues = []
    if not set(USER_SELECT.split(",")) <= user.keys():
        issues.append("User response is missing selected identity properties.")
    try:
        uuid.UUID(user.get("id", ""))
    except (ValueError, TypeError, AttributeError):
        issues.append("User has no valid object ID.")
    if user.get("userPrincipalName", "").lower() != participant.upn.lower():
        issues.append("User UPN mismatch.")
    if user.get("userType") != "Guest" or user.get("accountEnabled") is not True:
        issues.append("User must be an enabled Guest.")
    if (
        user.get("creationType") is not None or user.get("externalUserState") is not None
        or user.get("onPremisesSyncEnabled") is True
    ):
        issues.append("User is not the expected cloud-only Internal Guest.")
    marker = (user.get("onPremisesExtensionAttributes") or {}).get("extensionAttribute15")
    if marker != participant.config.marker:
        issues.append("User ownership marker mismatch; do not adopt this account.")
    return issues


def rg_issues(group: dict[str, Any], participant: Participant) -> list[str]:
    issues = []
    if (
        group.get("id", "").lower() != participant.scope.lower()
        or group.get("name", "").lower() != participant.rg
        or group.get("location", "").lower() != participant.config.location
    ):
        issues.append("RG ID/name/location mismatch.")
    tags = group.get("tags") or {}
    if any(tags.get(key) != value for key, value in participant.tags.items()):
        issues.append("RG ownership tags mismatch; do not adopt this RG.")
    if group.get("properties", {}).get("provisioningState") != "Succeeded":
        issues.append("RG provisioningState is not Succeeded.")
    return issues


def audit_access(
    client: AzureClient, participant: Participant, user: dict[str, Any],
    assignments: list[dict[str, Any]],
    directory_assignments: list[dict[str, Any]],
) -> tuple[list[str], set[tuple[str, str]]]:
    user_id = user["id"].lower()
    members = client.collection(f"{GRAPH}/users/{user_id}/transitiveMemberOf")
    principals = {user_id}
    issues = []
    for member in members:
        kind = member.get("@odata.type")
        if not isinstance(member.get("id"), str) or not kind:
            raise WorkshopError("Incomplete transitive membership response; cannot audit access.")
        if kind == "#microsoft.graph.group":
            principals.add(member["id"].lower())
        elif kind == "#microsoft.graph.directoryRole":
            issues.append("Unexpected active Entra administrator role membership.")
        elif kind != "#microsoft.graph.administrativeUnit":
            raise WorkshopError("Unknown transitive membership type; cannot audit access.")
    for assignment in directory_assignments:
        if assignment["principalId"].lower() in principals:
            issues.append(
                "Unexpected active Entra role assignment at "
                f"{assignment.get('directoryScopeId') or assignment.get('appScopeId')}."
            )
    present = set()
    for assignment in assignments:
        prop = assignment.get("properties", {})
        principal = prop.get("principalId", "").lower()
        if principal not in principals:
            continue
        pair = (
            prop.get("scope", "").lower(),
            prop.get("roleDefinitionId", "").rsplit("/", 1)[-1].lower(),
        )
        if (
            principal != user_id or pair not in participant.expected_roles
            or prop.get("condition") or prop.get("delegatedManagedIdentityResourceId")
            or prop.get("principalType") != "User" or pair in present
        ):
            issues.append(
                f"Unexpected/conditional/group/duplicate Azure role: {pair[1]} at {pair[0]}."
            )
        else:
            present.add(pair)
    return issues, present


def check_private(path: Path, directory: bool = False) -> None:
    info = path.lstat()
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not correct_type or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise WorkshopError(f"Private path must be owned by you and mode 0700/0600: {path}")


def run_path(config: Config) -> Path:
    return Path(".workshop-runs") / config.workshopId


def read_state(config: Config, domain: str) -> dict[str, Any]:
    folder = run_path(config)
    for directory in (folder.parent, folder):
        if directory.exists() or directory.is_symlink():
            check_private(directory, directory=True)
    path = folder / "state.private.json"
    binding_config = asdict(config)
    # Omitted optional settings must retain existing configuration bindings.
    if not config.seTestAccountCount:
        del binding_config["seTestAccountCount"]
    if config.namePrefix is None:
        del binding_config["namePrefix"]
    if config.nameFormat is None:
        del binding_config["nameFormat"]
    binding = hashlib.sha256(
        json.dumps({"config": binding_config, "domain": domain}, sort_keys=True).encode()
    ).hexdigest()
    if not path.exists() and not path.is_symlink():
        return {"binding": binding, "participants": {}}
    check_private(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkshopError("Cannot read private state; restore its approved backup.") from exc
    if (
        not isinstance(data, dict) or data.get("binding") != binding
        or not isinstance(data.get("participants"), dict)
        or not all(isinstance(item, dict) for item in data["participants"].values())
    ):
        raise WorkshopError("Private state/config mismatch. Use the original config or a new ID.")
    return data


class RunStore:
    def __init__(self, config: Config):
        self.config = config
        self.folder = run_path(config)
        self.lock = None

    def __enter__(self) -> "RunStore":
        for directory in (self.folder.parent, self.folder):
            directory.mkdir(mode=0o700, exist_ok=True)
            check_private(directory, directory=True)
        lock_path = self.folder / "run.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        self.lock = os.fdopen(descriptor, "a")
        try:
            check_private(lock_path)
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (OSError, WorkshopError) as exc:
            self.lock.close()
            raise WorkshopError("Run directory is unsafe or another command holds its lock.") from exc
        return self

    def __exit__(self, *args) -> None:
        if self.lock:
            self.lock.close()

    def write(self, name: str, text: str) -> None:
        path = self.folder / name
        if path.exists() or path.is_symlink():
            check_private(path)
        descriptor, temporary = tempfile.mkstemp(prefix=".write-", dir=self.folder)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
                os.fchmod(stream.fileno(), 0o600)
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def save_state(self, state: dict[str, Any]) -> None:
        self.write("state.private.json", json.dumps(state, indent=2) + "\n")
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        header = [
            "participantId", "userPrincipalName", "objectId",
            "resourceGroup", "initialPassword", "status",
        ]
        if self.config.seTestAccountCount:
            header.insert(1, "accountPurpose")
        writer.writerow(header)
        for number, item in sorted(state["participants"].items()):
            row = [
                number, item["upn"], item.get("objectId", ""),
                item["resourceGroup"], item["initialPassword"],
                "created" if item.get("objectId") else "pending",
            ]
            if self.config.seTestAccountCount:
                row.insert(1, item["accountPurpose"])
            writer.writerow(row)
        self.write("credentials.private.csv", output.getvalue())


def report_header(config: Config) -> dict[str, Any]:
    return {
        "workshopId": config.workshopId,
        "tenantId": config.tenantId,
        "subscriptionId": config.subscriptionId,
        "location": config.location,
        "expectedParticipants": config.participantCount,
        "expectedSeTestAccounts": config.seTestAccountCount,
        "namePrefix": config.namePrefix,
        "nameFormat": config.nameFormat,
        "checkedAtUtc": utc_now(),
    }
