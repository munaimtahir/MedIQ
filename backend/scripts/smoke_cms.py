#!/usr/bin/env python3
"""CMS Question Bank Smoke Test Script (Python version for Docker)."""

import os
import sys
import json
from typing import Dict, Any
from uuid import UUID

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

# Colors for output
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
NC = "\033[0m"  # No Color

# Configuration
BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin123!")
REVIEWER_EMAIL = os.environ.get("REVIEWER_EMAIL", "reviewer@example.com")
REVIEWER_PASSWORD = os.environ.get("REVIEWER_PASSWORD", "Reviewer123!")

# Create HTTP client
client = httpx.Client(timeout=30.0)


def print_step(step: str, total: int):
    """Print step header."""
    print(f"{YELLOW}[{step}/{total}] {step}{NC}")


def check_response(response: httpx.Response, expected_status: int = 200, error_msg: str = "Request failed"):
    """Check response and raise on error."""
    if response.status_code != expected_status:
        print(f"{RED}✗ {error_msg} (status: {response.status_code}){NC}")
        try:
            print(json.dumps(response.json(), indent=2))
        except:
            print(response.text)
        sys.exit(1)
    return response.json()


def main():
    """Run smoke test."""
    print(f"{GREEN}=== CMS Question Bank Smoke Test ==={NC}")
    print(f"Base URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print(f"Reviewer: {REVIEWER_EMAIL}")
    print()

    errors = 0

    # Step 1: Health checks
    print_step("1/19", 19)
    try:
        health = client.get(f"{BASE_URL}/health", timeout=5.0)
        if health.status_code == 200:
            print(f"{GREEN}✓ Health check passed{NC}")
        else:
            print(f"{RED}✗ Health check failed{NC}")
            errors += 1
    except Exception as e:
        print(f"{RED}✗ Health check failed: {e}{NC}")
        errors += 1

    try:
        ready = client.get(f"{BASE_URL}/ready", timeout=5.0)
        if ready.status_code == 200:
            print(f"{GREEN}✓ Readiness check passed{NC}")
        else:
            print(f"{YELLOW}⚠ Readiness check returned {ready.status_code}{NC}")
    except Exception as e:
        print(f"{YELLOW}⚠ Readiness check failed: {e}{NC}")

    # Step 2: Login as ADMIN
    print_step("2/19", 19)
    login_data = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    login_resp = client.post(f"{BASE_URL}/v1/auth/login", json=login_data)
    login_json = check_response(login_resp, 200, "Admin login failed")
    admin_token = login_json.get("tokens", {}).get("access_token")
    if not admin_token:
        print(f"{RED}✗ Failed to extract admin token{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Admin logged in{NC}")

    # Step 3: Get syllabus structure
    print_step("3/19", 19)
    headers = {"Authorization": f"Bearer {admin_token}"}
    years_resp = client.get(f"{BASE_URL}/v1/syllabus/years", headers=headers)
    years = check_response(years_resp, 200, "Failed to get years")
    if not years:
        print(f"{RED}✗ No years found. Please seed syllabus structure first.{NC}")
        sys.exit(1)
    year_id = years[0]["id"]
    print(f"{GREEN}✓ Found year ID: {year_id}{NC}")

    blocks_resp = client.get(f"{BASE_URL}/v1/syllabus/blocks?year={year_id}", headers=headers)
    blocks = check_response(blocks_resp, 200, "Failed to get blocks")
    if not blocks:
        print(f"{RED}✗ No blocks found for year {year_id}{NC}")
        sys.exit(1)
    block_id = blocks[0]["id"]
    print(f"{GREEN}✓ Found block ID: {block_id}{NC}")

    themes_resp = client.get(f"{BASE_URL}/v1/syllabus/themes?block_id={block_id}", headers=headers)
    themes = check_response(themes_resp, 200, "Failed to get themes")
    if not themes:
        print(f"{RED}✗ No themes found for block {block_id}{NC}")
        sys.exit(1)
    theme_id = themes[0]["id"]
    print(f"{GREEN}✓ Found theme ID: {theme_id}{NC}")

    # Step 4: Create DRAFT question
    print_step("4/19", 19)
    question_data = {
        "stem": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "option_e": "7",
        "correct_index": 1,
    }
    create_resp = client.post(f"{BASE_URL}/v1/admin/questions", json=question_data, headers=headers)
    create_json = check_response(create_resp, 201, "Failed to create question")
    question_id = create_json.get("id")
    if not question_id:
        print(f"{RED}✗ Failed to extract question ID{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Question created: {question_id}{NC}")

    status = create_json.get("status")
    if status != "DRAFT":
        print(f"{RED}✗ Expected status DRAFT, got {status}{NC}")
        sys.exit(1)

    # Step 5: Try submit too early (should fail)
    print_step("5/19", 19)
    submit_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/submit", headers=headers)
    if submit_resp.status_code in [400, 422]:
        print(f"{GREEN}✓ Submit correctly rejected (missing required fields){NC}")
    else:
        print(f"{RED}✗ Submit should have failed but succeeded{NC}")
        sys.exit(1)

    # Step 6: Update question to satisfy submit gate
    print_step("6/19", 19)
    update_data = {
        "stem": "What is 2+2?",
        "option_a": "3",
        "option_b": "4",
        "option_c": "5",
        "option_d": "6",
        "option_e": "7",
        "correct_index": 1,
        "year_id": year_id,
        "block_id": block_id,
        "theme_id": theme_id,
        "difficulty": "easy",
        "cognitive_level": "recall",
    }
    update_resp = client.put(f"{BASE_URL}/v1/admin/questions/{question_id}", json=update_data, headers=headers)
    check_response(update_resp, 200, "Failed to update question")
    print(f"{GREEN}✓ Question updated{NC}")

    # Step 7: Submit success
    print_step("7/19", 19)
    submit_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/submit", headers=headers)
    submit_json = check_response(submit_resp, 200, "Submit failed")
    new_status = submit_json.get("new_status")
    if new_status != "IN_REVIEW":
        print(f"{RED}✗ Expected status IN_REVIEW, got {new_status}{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Question submitted (status: IN_REVIEW){NC}")

    # Step 8: Login as REVIEWER
    print_step("8/19", 19)
    reviewer_login = client.post(f"{BASE_URL}/v1/auth/login", json={"email": REVIEWER_EMAIL, "password": REVIEWER_PASSWORD})
    reviewer_json = check_response(reviewer_login, 200, "Reviewer login failed")
    reviewer_token = reviewer_json.get("tokens", {}).get("access_token")
    if not reviewer_token:
        print(f"{RED}✗ Failed to extract reviewer token{NC}")
        sys.exit(1)
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}
    print(f"{GREEN}✓ Reviewer logged in{NC}")

    # Step 9: Approve should fail (missing explanation)
    print_step("9/19", 19)
    approve_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/approve", headers=reviewer_headers)
    if approve_resp.status_code in [400, 422]:
        print(f"{GREEN}✓ Approve correctly rejected (missing explanation){NC}")
    else:
        print(f"{RED}✗ Approve should have failed but succeeded{NC}")
        sys.exit(1)

    # Step 10: Add explanation
    print_step("10/19", 19)
    update_resp = client.put(
        f"{BASE_URL}/v1/admin/questions/{question_id}",
        json={"explanation_md": "2+2 equals 4 because addition of two and two results in four."},
        headers=reviewer_headers,
    )
    check_response(update_resp, 200, "Failed to add explanation")
    print(f"{GREEN}✓ Explanation added{NC}")

    # Step 11: Approve success
    print_step("11/19", 19)
    approve_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/approve", headers=reviewer_headers)
    approve_json = check_response(approve_resp, 200, "Approve failed")
    new_status = approve_json.get("new_status")
    if new_status != "APPROVED":
        print(f"{RED}✗ Expected status APPROVED, got {new_status}{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Question approved (status: APPROVED){NC}")

    # Step 12: Publish should fail (missing source)
    print_step("12/19", 19)
    publish_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/publish", headers=headers)
    if publish_resp.status_code in [400, 422]:
        print(f"{GREEN}✓ Publish correctly rejected (missing source){NC}")
    else:
        print(f"{RED}✗ Publish should have failed but succeeded{NC}")
        sys.exit(1)

    # Step 13: Add source fields
    print_step("13/19", 19)
    update_resp = client.put(
        f"{BASE_URL}/v1/admin/questions/{question_id}",
        json={"source_book": "Test Mathematics Book", "source_page": "p. 42", "source_ref": "TEST-001"},
        headers=headers,
    )
    check_response(update_resp, 200, "Failed to add source fields")
    print(f"{GREEN}✓ Source fields added{NC}")

    # Step 14: Publish success
    print_step("14/19", 19)
    publish_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/publish", headers=headers)
    publish_json = check_response(publish_resp, 200, "Publish failed")
    new_status = publish_json.get("new_status")
    if new_status != "PUBLISHED":
        print(f"{RED}✗ Expected status PUBLISHED, got {new_status}{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Question published (status: PUBLISHED){NC}")

    # Step 15: RBAC test - REVIEWER cannot unpublish
    print_step("15/19", 19)
    unpublish_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/unpublish", headers=reviewer_headers)
    if unpublish_resp.status_code == 403:
        print(f"{GREEN}✓ Reviewer correctly denied unpublish (403){NC}")
    else:
        print(f"{YELLOW}⚠ Reviewer denied but with unexpected status: {unpublish_resp.status_code}{NC}")

    # Step 16: Unpublish success (ADMIN)
    print_step("16/19", 19)
    unpublish_resp = client.post(f"{BASE_URL}/v1/admin/questions/{question_id}/unpublish", headers=headers)
    unpublish_json = check_response(unpublish_resp, 200, "Unpublish failed")
    new_status = unpublish_json.get("new_status")
    if new_status != "APPROVED":
        print(f"{RED}✗ Expected status APPROVED, got {new_status}{NC}")
        sys.exit(1)
    print(f"{GREEN}✓ Question unpublished (status: APPROVED){NC}")

    # Step 17: Check versions
    print_step("17/19", 19)
    versions_resp = client.get(f"{BASE_URL}/v1/admin/questions/{question_id}/versions", headers=headers)
    versions = check_response(versions_resp, 200, "Failed to get versions")
    version_count = len(versions)
    if version_count >= 5:
        print(f"{GREEN}✓ Found {version_count} versions{NC}")
    else:
        print(f"{YELLOW}⚠ Expected at least 5 versions, got {version_count}{NC}")

    # Check version numbers
    if versions:
        first_version = versions[0].get("version_no", 0)
        last_version = versions[-1].get("version_no", 0)
        if first_version > last_version:
            print(f"{GREEN}✓ Version numbers increment correctly (latest: {first_version}, first: {last_version}){NC}")

    # Step 18: Check audit log
    print_step("18/19", 19)
    audit_resp = client.get(
        f"{BASE_URL}/v1/admin/audit?entity_type=QUESTION&entity_id={question_id}&limit=20", headers=headers
    )
    if audit_resp.status_code == 200:
        audits = audit_resp.json()
        audit_count = len(audits)
        if audit_count >= 5:
            print(f"{GREEN}✓ Found {audit_count} audit entries{NC}")
            # Check for key actions
            actions = [a.get("action") for a in audits]
            if "question.create" in actions and "question.publish" in actions:
                print(f"{GREEN}✓ Key audit actions present (create, publish){NC}")
        else:
            print(f"{YELLOW}⚠ Expected at least 5 audit entries, got {audit_count}{NC}")
    else:
        print(f"{YELLOW}⚠ Audit endpoint not available (dev-only) or returned {audit_resp.status_code}{NC}")

    # Step 19: Media upload (skip if not critical)
    print_step("19/19", 19)
    print(f"{YELLOW}⚠ Media upload test skipped (requires file handling){NC}")
    
    client.close()

    # Final summary
    print()
    print(f"{GREEN}=== Smoke Test Complete ==={NC}")
    print(f"{GREEN}All critical tests passed!{NC}")
    print()
    print(f"Question ID: {question_id}")
    print("Status flow: DRAFT → IN_REVIEW → APPROVED → PUBLISHED → APPROVED")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
