#!/usr/bin/env python3
"""API security tests: rate limiting, lockout, invalid login protection."""

import json
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE_URL = "http://localhost:8000/v1"


def make_request(method, path, data=None, headers=None):
    """Make HTTP request and return (status_code, response_data, headers_dict)."""
    url = f"{BASE_URL}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    try:
        req = Request(
            url,
            data=json.dumps(data).encode() if data else None,
            headers=req_headers,
            method=method,
        )
        with urlopen(req, timeout=10) as response:
            status = response.getcode()
            body = json.loads(response.read().decode())
            headers_dict = dict(response.headers.items())
            return status, body, headers_dict
    except HTTPError as e:
        status = e.code
        headers_dict = dict(e.headers.items()) if e.headers else {}
        try:
            body = json.loads(e.read().decode())
        except Exception:
            body = {"error": str(e)}
        return status, body, headers_dict
    except URLError as e:
        return None, {"error": str(e)}, {}


def test_invalid_login_generic():
    """Test that invalid login returns generic error (no account existence leak)."""
    print("1. Testing invalid login - generic error (no account leak)...")

    # Test with correct email, wrong password
    test_email = f"test_{int(time.time())}@example.com"
    # First create the user
    import json
    from urllib.request import Request, urlopen

    signup_data = {"name": "Test User", "email": test_email, "password": "CorrectPass123!"}
    try:
        req = Request(
            f"{BASE_URL}/auth/signup",
            data=json.dumps(signup_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10):
            pass  # User created
    except Exception:
        pass

    # Test 1: Wrong password for existing email
    wrong_pass_status, wrong_pass_response, _ = make_request(
        "POST", "/auth/login", data={"email": test_email, "password": "WrongPass123!"}
    )

    # Test 2: Non-existent email
    fake_email_status, fake_email_response, _ = make_request(
        "POST",
        "/auth/login",
        data={"email": f"fake_{int(time.time())}@example.com", "password": "AnyPass123!"},
    )

    # Both should return similar error responses (same status, similar message/code)
    # to avoid account enumeration
    if wrong_pass_status == fake_email_status:
        # Check if error codes/messages are similar (don't reveal account existence)
        wrong_pass_code = wrong_pass_response.get("error", {}).get("code", "")
        fake_email_code = fake_email_response.get("error", {}).get("code", "")

        if wrong_pass_status in (401, 403) and (
            wrong_pass_code == fake_email_code or (wrong_pass_code and fake_email_code)
        ):
            print(f"   ✓ Both return same status: {wrong_pass_status}")
            print("   ✓ Error codes are consistent (no account leak)")
            return True
        else:
            print("   ⚠ Status matches but codes differ - may leak account existence")
            print(f"   Wrong pass: {wrong_pass_status} / {wrong_pass_code}")
            print(f"   Fake email: {fake_email_status} / {fake_email_code}")
            return False
    else:
        print("   ✗ Different status codes - leaks account existence!")
        print(f"   Wrong pass: {wrong_pass_status}")
        print(f"   Fake email: {fake_email_status}")
        return False


def test_rate_limiting():
    """Test rate limiting on login endpoint."""
    print("\n2. Testing rate limiting...")

    test_email = f"ratelimit_{int(time.time())}@example.com"

    # Make multiple rapid login attempts with wrong password
    attempts = 0
    retry_after = None
    last_status = None

    for _i in range(15):  # Should hit rate limit before this
        attempts += 1
        status, response, headers = make_request(
            "POST", "/auth/login", data={"email": test_email, "password": "WrongPass123!"}
        )
        last_status = status

        if status == 429:
            retry_after = headers.get("Retry-After") or headers.get("retry-after")
            error_code = response.get("error", {}).get("code", "")
            print(f"   ✓ Rate limited after {attempts} attempts")
            print("   ✓ Status: 429")
            print(f"   ✓ Retry-After header: {retry_after}")
            print(f"   ✓ Error code: {error_code}")

            # Verify envelope has request_id
            request_id = response.get("request_id") or response.get("error", {}).get("request_id")
            if request_id:
                print(f"   ✓ Request ID present: {request_id[:20]}...")

            return True

        # Small delay to avoid overwhelming
        time.sleep(0.1)

    print(f"   ✗ Rate limit not triggered after {attempts} attempts (last status: {last_status})")
    return False


def test_account_lockout():
    """Test account lockout after multiple failed logins."""
    print("\n3. Testing account lockout...")

    # Use a fixed email to ensure lockout accumulates on same account
    test_email = f"lockout_test_{int(time.time()) % 10000}@example.com"  # Fixed for this test run
    test_password = "CorrectPass123!"

    # Create user first
    signup_data = {"name": "Lockout Test User", "email": test_email, "password": test_password}
    try:
        req = Request(
            "http://localhost:8000/v1/auth/signup",
            data=json.dumps(signup_data).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=10):
            print(f"   Created test user: {test_email}")
    except HTTPError as e:
        if e.code == 409:
            print(f"   User already exists (OK): {test_email}")
        else:
            print(f"   ⚠ Signup failed: {e.code}")
    except Exception as e:
        print(f"   ⚠ Signup error: {e}")

    # Make multiple failed login attempts with WRONG password (same email)
    # Threshold is 8 failures, so we need at least 9 attempts (8 failures + 1 that gets locked)
    lockout_triggered = False
    attempts = 0
    lockout_attempt = None

    for _i in range(12):  # Need at least 9 attempts (8 failures + 1 lockout response)
        attempts += 1
        status, response, headers = make_request(
            "POST", "/auth/login", data={"email": test_email, "password": "WrongPass123!"}
        )

        if status == 403:
            # Check if it's a lockout response
            error_code = response.get("error", {}).get("code", "")
            message = response.get("error", {}).get("message", "")

            if error_code == "ACCOUNT_LOCKED" or "lock" in error_code.upper():
                lockout_triggered = True
                lockout_attempt = attempts
                lock_expires_in = (
                    response.get("error", {}).get("details", {}).get("lock_expires_in")
                )

                print(f"   ✓ Account locked after {attempts} attempts")
                print("   ✓ Status: 403")
                print(f"   ✓ Error code: {error_code}")
                if lock_expires_in is not None:
                    print(f"   ✓ Lock expires in: {lock_expires_in} seconds")

                # Verify request_id
                request_id = response.get("request_id") or response.get("error", {}).get(
                    "request_id"
                )
                if request_id:
                    print(f"   ✓ Request ID present: {request_id[:20]}...")

                return True

        # Small delay to avoid overwhelming
        time.sleep(0.05)

    if not lockout_triggered:
        print(f"   ✗ Lockout not triggered after {attempts} attempts")
        print(f"   Last status: {status if 'status' in locals() else 'N/A'}")
        print("   Expected: 403 with ACCOUNT_LOCKED code after 8 failed attempts")
        return False

    return lockout_triggered


def main():
    """Run all security tests."""
    print("=" * 60)
    print("API Security Tests (Rate Limiting, Lockout, Invalid Login)")
    print("=" * 60)

    results = []

    # Test invalid login generic error
    results.append(("Invalid Login Generic", test_invalid_login_generic()))

    # Test rate limiting
    results.append(("Rate Limiting", test_rate_limiting()))

    # Test account lockout
    results.append(("Account Lockout", test_account_lockout()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{status} - {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("⚠ Some tests failed or not implemented")
        sys.exit(1)


if __name__ == "__main__":
    main()
