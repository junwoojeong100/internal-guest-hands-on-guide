#!/usr/bin/env python3
"""Plan by default; --apply provisions only workshop identities, RGs and RBAC."""

import argparse
from contextlib import nullcontext
import json
import secrets
import sys
import time
import uuid

from workshop_common import (
    AUTH_API, GRAPH, RG_API, AzureClient, Config, RunStore, WorkshopError,
    api_url, audit_access, directory_snapshot, get_rg, get_user, preflight, read_state, report_header,
    rg_issues, role_snapshot, user_issues,
)


def provision(client: AzureClient, config: Config, apply: bool = False) -> dict:
    with RunStore(config) if apply else nullcontext() as store:
        domain, missing_providers = preflight(client, config)
        state = read_state(config, domain)
        assignments = role_snapshot(client, config)
        directory_assignments = directory_snapshot(client)
        rows = []
        for participant in config.participants(domain):
            user = get_user(client, participant)
            group = get_rg(client, participant)
            issues = []
            present = set()
            saved = state["participants"].get(participant.number)
            if saved and (
                saved.get("upn") != participant.upn
                or saved.get("resourceGroup") != participant.rg
                or not isinstance(saved.get("initialPassword"), str)
                or len(saved["initialPassword"]) < 24
            ):
                issues.append("Private participant state mismatch; restore its backup.")
            if user:
                issues.extend(user_issues(user, participant))
                if not saved:
                    issues.append("Existing account has no private credential journal; no reset.")
                elif saved.get("objectId") and saved["objectId"] != user.get("id"):
                    issues.append("User object ID differs from the private journal.")
                if not issues:
                    access_issues, present = audit_access(
                        client, participant, user, assignments, directory_assignments
                    )
                    issues.extend(access_issues)
            elif saved and saved.get("objectId"):
                issues.append("Previously created user disappeared; do not silently recreate it.")
            if group:
                issues.extend(rg_issues(group, participant))
                if not user:
                    issues.append("Existing RG has no original participant; review before reuse.")
            if issues:
                raise WorkshopError(f"{participant.alias}: " + " ".join(issues))
            rows.append((participant, user, group, participant.expected_roles - present))
        plan = {
            **report_header(config), "mode": "apply" if apply else "plan",
            "createUsers": sum(user is None for _, user, _, _ in rows),
            "createResourceGroups": sum(group is None for _, _, group, _ in rows),
            "createRoleAssignments": sum(len(missing) for _, _, _, missing in rows),
            "registerProviders": missing_providers,
            "participants": [
                {"participantId": p.number, "upn": p.upn, "resourceGroup": p.rg}
                for p, _, _, _ in rows
            ],
        }
        if not apply:
            return plan
        for provider in missing_providers:
            path = config.scope + "/providers/" + provider
            client.request("POST", api_url(path + "/register", "2021-04-01"))
            deadline = time.monotonic() + 300
            while client.request("GET", api_url(path, "2021-04-01")).get(
                "registrationState"
            ) != "Registered":
                if time.monotonic() >= deadline:
                    raise WorkshopError(f"Provider registration timed out: {provider}. Rerun later.")
                time.sleep(5)
        for participant, user, group, missing in rows:
            if not user:
                if participant.number not in state["participants"]:
                    state["participants"][participant.number] = {
                        "upn": participant.upn, "resourceGroup": participant.rg,
                        "initialPassword": "Aq9!" + secrets.token_urlsafe(24),
                    }
                # Persist the secret before POST so a lost response can be reconciled.
                store.save_state(state)
                saved = state["participants"][participant.number]
                user = client.request("POST", f"{GRAPH}/users", {
                    "accountEnabled": True, "userType": "Guest",
                    "displayName": f"Foundry workshop {participant.alias}",
                    "mailNickname": participant.alias, "userPrincipalName": participant.upn,
                    "passwordProfile": {
                        "forceChangePasswordNextSignIn": True,
                        "password": saved["initialPassword"],
                    },
                    "onPremisesExtensionAttributes": {
                        "extensionAttribute15": config.marker,
                    },
                })
                try:
                    uuid.UUID(user["id"])
                except (KeyError, ValueError, TypeError, AttributeError) as exc:
                    raise WorkshopError("Create-user response has no valid ID. Rerun safely.") from exc
            saved = state["participants"][participant.number]
            saved["objectId"] = user["id"]
            store.save_state(state)
            if not group:
                client.request("PUT", api_url(participant.scope, RG_API), {
                    "location": config.location, "tags": participant.tags,
                })
            for scope, role in sorted(missing):
                assignment = uuid.uuid5(
                    uuid.NAMESPACE_URL, f"{scope}|{user['id'].lower()}|{role}"
                )
                client.request("PUT", api_url(
                    scope + "/providers/Microsoft.Authorization/roleAssignments/"
                    + str(assignment), AUTH_API,
                ), {"properties": {
                    "principalId": user["id"], "principalType": "User",
                    "roleDefinitionId": (
                        config.scope + "/providers/Microsoft.Authorization/roleDefinitions/" + role
                    ),
                }})
            print(f"Prepared {participant.number}/{config.participantCount:03d}", file=sys.stderr)
        store.write("provision.private.json", json.dumps(plan, indent=2) + "\n")
        plan["next"] = "Run verify_workshop.py independently; apply is not a verification result."
        return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Workshop JSON config path")
    parser.add_argument("--apply", action="store_true", help="Explicitly create missing objects")
    args = parser.parse_args(argv)
    try:
        config = Config.load(args.config)
        result = provision(AzureClient(config), config, apply=args.apply)
        print(json.dumps(result, indent=2))
        return 0
    except (WorkshopError, OSError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
