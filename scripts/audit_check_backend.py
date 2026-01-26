#!/usr/bin/env python3
"""
Parse pip-audit JSON, optionally resolve severity via OSV, apply allowlist, fail on CRITICAL
(and optionally HIGH if FAIL_ON_HIGH=1). Produces backend-audit.json as artifact; this script
gates CI.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ALLOWLIST_PATH = Path(__file__).resolve().parents[1] / "docs" / "security_allowlist_vulns.json"
OSV_BASE = "https://api.osv.dev/v1/vulns"


def load_allowlist() -> list[dict]:
    if not ALLOWLIST_PATH.exists():
        return []
    with open(ALLOWLIST_PATH) as f:
        data = json.load(f)
    return data.get("backend") or []


def is_allowlisted(vuln_id: str, allowlist: list[dict]) -> bool:
    today = date.today()
    for entry in allowlist:
        vid = (entry.get("id") or "").strip()
        if not vid or vid.upper() != vuln_id.upper():
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


def fetch_osv_severity(vuln_id: str, cache: dict[str, str]) -> str:
    if vuln_id in cache:
        return cache[vuln_id]
    # Prefer CVE for OSV; accept GHSA, PYSEC
    osv_id = vuln_id
    url = f"{OSV_BASE}/{osv_id}"
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except (HTTPError, URLError, json.JSONDecodeError, OSError):
        cache[vuln_id] = "UNKNOWN"
        return "UNKNOWN"
    sev = "LOW"
    db = data.get("database_specific") or {}
    if isinstance(db.get("severity"), str):
        sev = (db["severity"] or "LOW").upper()
    else:
        for s in data.get("severity", []) or []:
            if s.get("type") == "CVSS_V3" and "score" in s:
                try:
                    sc = float(s["score"])
                except (TypeError, ValueError):
                    continue
                if sc >= 9.0:
                    sev = "CRITICAL"
                elif sc >= 7.0:
                    sev = "HIGH"
                elif sc >= 4.0:
                    sev = "MEDIUM"
                else:
                    sev = "LOW"
                break
    cache[vuln_id] = sev
    return sev


def main() -> int:
    audit_path = Path(os.environ.get("AUDIT_JSON", "backend-audit.json"))
    if not audit_path.is_absolute():
        audit_path = Path.cwd() / audit_path
    if not audit_path.exists():
        print(f"audit_check_backend: {audit_path} not found")
        return 1
    with open(audit_path) as f:
        report = json.load(f)
    allowlist = load_allowlist()
    fail_on_high = os.environ.get("FAIL_ON_HIGH", "").strip().lower() in ("1", "true", "yes")
    cache: dict[str, str] = {}
    critical: list[tuple[str, str, str]] = []
    high: list[tuple[str, str, str]] = []

    for dep in report.get("dependencies") or []:
        pkg = dep.get("name", "?")
        ver = dep.get("version", "?")
        for v in dep.get("vulns") or []:
            vid = v.get("id") or ""
            aliases = v.get("aliases") or []
            ids_to_check = [vid] + [a for a in aliases if isinstance(a, str)]
            if any(is_allowlisted(aid, allowlist) for aid in ids_to_check):
                continue
            lookup = next((a for a in ids_to_check if a.startswith("CVE-") or a.startswith("GHSA-")), vid)
            sev = fetch_osv_severity(lookup, cache)
            if sev == "CRITICAL":
                critical.append((pkg, ver, vid))
            elif fail_on_high and sev == "HIGH":
                high.append((pkg, ver, vid))

    if critical:
        print("CRITICAL vulnerabilities (CI fails):")
        for pkg, ver, vid in critical:
            print(f"  {pkg} {ver}: {vid}")
    if high:
        print("HIGH vulnerabilities (CI fails when FAIL_ON_HIGH=1):")
        for pkg, ver, vid in high:
            print(f"  {pkg} {ver}: {vid}")
    if critical or high:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
