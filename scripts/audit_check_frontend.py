#!/usr/bin/env python3
"""
Parse pnpm audit --json, apply allowlist, fail only if CRITICAL present (and not allowlisted).
Produces frontend-audit.json as artifact; this script gates CI.
"""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path

ALLOWLIST_PATH = Path(__file__).resolve().parents[1] / "docs" / "security_allowlist_vulns.json"


def load_allowlist() -> list[dict]:
    if not ALLOWLIST_PATH.exists():
        return []
    with open(ALLOWLIST_PATH) as f:
        data = json.load(f)
    return data.get("frontend") or []


def is_allowlisted(advisory_id: str, cves: list[str], ghsas: list[str], allowlist: list[dict]) -> bool:
    today = date.today()
    ids_to_check = [advisory_id] + cves + ghsas
    for entry in allowlist:
        vid = (entry.get("id") or "").strip()
        if not vid:
            continue
        if not any(vid.upper() == x.upper() for x in ids_to_check):
            continue
        ex = entry.get("expires")
        if not ex:
            continue
        try:
            exp = datetime.fromisoformat(str(ex).replace("Z", "+00:00")).date()
        except Exception:
            try:
                exp = date.fromisoformat(str(ex))
            except Exception:
                exp = None
        if exp is not None and today <= exp:
            return True
    return False


def main() -> int:
    audit_path = Path(os.environ.get("AUDIT_JSON", "frontend-audit.json"))
    if not audit_path.is_absolute():
        audit_path = Path.cwd() / audit_path
    if not audit_path.exists():
        print(f"audit_check_frontend: {audit_path} not found")
        return 1
    with open(audit_path) as f:
        report = json.load(f)
    allowlist = load_allowlist()
    advisories = report.get("advisories") or {}
    critical: list[tuple[str, str]] = []

    for aid, adv in advisories.items():
        sev = (adv.get("severity") or "").lower()
        if sev != "critical":
            continue
        cves = adv.get("cves") or []
        ghsas = [adv.get("github_advisory_id")] if adv.get("github_advisory_id") else []
        if is_allowlisted(str(aid), cves, ghsas, allowlist):
            continue
        module = adv.get("module_name", "?")
        critical.append((module, aid))

    if critical:
        print("CRITICAL vulnerabilities (CI fails):")
        for module, aid in critical:
            print(f"  {module}: advisory {aid}")
        return 1
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
