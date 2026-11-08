#!/usr/bin/env python3
"""Independently read Azure/Graph state; fail on missing or unexpected access."""

import argparse
import json
import sys

from workshop_common import (
    AzureClient, Config, RunStore, WorkshopError, audit_access, directory_snapshot, get_rg, get_user,
    preflight, report_header, rg_issues, role_snapshot, user_issues,
)


def verify(client: AzureClient, config: Config) -> dict:
    domain, missing_providers = preflight(client, config)
    assignments = role_snapshot(client, config)
    directory_assignments = directory_snapshot(client)
    checks = []
    for participant in config.participants(domain):
        user = get_user(client, participant)
        group = get_rg(client, participant)
        issues = []
        if not user:
            issues.append("Missing participant account.")
        else:
            issues.extend(user_issues(user, participant))
            if not issues:
                access_issues, present = audit_access(
                    client, participant, user, assignments, directory_assignments
                )
                issues.extend(access_issues)
                for scope, role in sorted(participant.expected_roles - present):
                    issues.append(f"Missing required direct role: {role} at {scope}.")
        if not group:
            issues.append("Missing resource group.")
        else:
            issues.extend(rg_issues(group, participant))
        checks.append({
            "participantId": participant.number, "upn": participant.upn,
            "resourceGroup": participant.rg, "objectId": user.get("id") if user else None,
            "issues": issues,
        })
    return {
        **report_header(config),
        "status": "complete",
        "passed": not missing_providers and not any(row["issues"] for row in checks),
        "missingProviders": missing_providers, "participants": checks,
        "limits": [
            "Snapshot of the target subscription, descendants and inherited assignments only.",
            "Other subscriptions/tenants, eligible PIM roles and future membership changes not audited.",
            "Does not test participant sign-in, MFA, Conditional Access, policy/deny effects or portal UI.",
            "Password-change behavior is not verified by this snapshot; existing accounts are not reset or repatched.",
            "Does not provision/test Foundry, models, TPM, project MI, cost or 50-user load.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Same config used for provisioning")
    args = parser.parse_args(argv)
    try:
        config = Config.load(args.config)
        with RunStore(config) as store:
            store.write("verification.private.json", json.dumps({
                **report_header(config), "passed": False, "status": "incomplete",
            }, indent=2) + "\n")
            try:
                result = verify(AzureClient(config), config)
            except (WorkshopError, OSError) as exc:
                store.write("verification.private.json", json.dumps({
                    **report_header(config), "passed": False, "status": "error",
                    "error": str(exc),
                }, indent=2) + "\n")
                raise
            store.write("verification.private.json", json.dumps(result, indent=2) + "\n")
        failed = [row for row in result["participants"] if row["issues"]]
        print(
            f"{'PASS' if result['passed'] else 'FAIL'}: "
            f"{len(result['participants']) - len(failed)}/{config.participantCount} participants; "
            f"{len(result['missingProviders'])} unregistered providers."
        )
        for row in failed:
            print(f"{row['participantId']}: " + " ".join(row["issues"]), file=sys.stderr)
        print(f"Private report: {store.folder}/verification.private.json")
        return 0 if result["passed"] else 1
    except (WorkshopError, OSError) as exc:
        print(f"FAILED (audit incomplete, not PASS): {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
