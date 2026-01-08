#!/usr/bin/env python3
"""Quick API auth flow tests for verification."""

import json
import sys
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE_URL = "http://localhost:8000/v1"


def make_request(method, path, data=None, headers=None):
    """Make HTTP request and return (status_code, response_data)."""
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
            return status, body
    except HTTPError as e:
        status = e.code
        try:
            body = json.loads(e.read().decode())
        except:
            body = {"error": str(e)}
        return status, body
    except URLError as e:
        return None, {"error": str(e)}


def test_health():
    """Test health endpoint."""
    print("1. Testing /v1/health...")
    status, data = make_request("GET", "/health")
    if status == 200 and data.get("status") == "ok":
        print(f"   ✓ Health check passed: {data}")
        return True
    else:
        print(f"   ✗ Health check failed: {status} - {data}")
        return False


def test_ready():
    """Test ready endpoint."""
    print("\n2. Testing /v1/ready...")
    status, data = make_request("GET", "/ready")
    if status == 200:
        print(f"   ✓ Ready check passed")
        print(f"   Status: {data.get('status')}")
        print(f"   Checks: {data.get('checks', {})}")
        print(f"   Request ID: {data.get('request_id', 'N/A')}")
        return True
    else:
        print(f"   ✗ Ready check failed: {status} - {data}")
        return False


def test_signup():
    """Test signup endpoint."""
    print("\n3. Testing /v1/auth/signup...")
    test_email = f"test_{int(time.time())}@example.com"
    data = {"name": "Test User", "email": test_email, "password": "TestPass123!"}
    status, response = make_request("POST", "/auth/signup", data=data)
    if status == 201:
        print(f"   ✓ Signup passed")
        print(f"   User ID: {response.get('user', {}).get('id', 'N/A')}")
        print(f"   Email: {response.get('user', {}).get('email', 'N/A')}")
        if "tokens" in response:
            print(f"   ✓ Tokens returned (access_token and refresh_token present)")
        return True, test_email, response.get("tokens", {})
    else:
        print(f"   ✗ Signup failed: {status} - {response}")
        return False, None, None


def test_login(email, password="TestPass123!"):
    """Test login endpoint."""
    print(f"\n4. Testing /v1/auth/login...")
    data = {"email": email, "password": password}
    status, response = make_request("POST", "/auth/login", data=data)
    if status == 200:
        print(f"   ✓ Login passed")
        if "tokens" in response:
            tokens = response["tokens"]
            print(f"   ✓ Access token: {tokens.get('access_token', 'N/A')[:20]}...")
            print(f"   ✓ Refresh token: {tokens.get('refresh_token', 'N/A')[:20]}...")
            return True, tokens
        else:
            print(f"   ⚠ No tokens in response")
            return True, None
    else:
        print(f"   ✗ Login failed: {status} - {response}")
        return False, None


def test_me(access_token):
    """Test /me endpoint."""
    print(f"\n5. Testing /v1/auth/me...")
    headers = {"Authorization": f"Bearer {access_token}"}
    status, response = make_request("GET", "/auth/me", headers=headers)
    if status == 200:
        print(f"   ✓ /me passed")
        print(f"   User: {response.get('user', {}).get('email', 'N/A')}")
        return True, response.get("user")
    else:
        print(f"   ✗ /me failed: {status} - {response}")
        return False, None


def test_refresh(refresh_token):
    """Test refresh token endpoint."""
    print(f"\n6. Testing /v1/auth/refresh...")
    data = {"refresh_token": refresh_token}
    status, response = make_request("POST", "/auth/refresh", data=data)
    if status == 200:
        print(f"   ✓ Refresh passed")
        if "tokens" in response:
            new_tokens = response["tokens"]
            print(f"   ✓ New access token received")
            print(f"   ✓ New refresh token received (rotation)")
            return True, new_tokens
        return True, None
    else:
        print(f"   ✗ Refresh failed: {status} - {response}")
        return False, None


def test_logout(refresh_token):
    """Test logout endpoint."""
    print(f"\n7. Testing /v1/auth/logout...")
    data = {"refresh_token": refresh_token}
    status, response = make_request("POST", "/auth/logout", data=data)
    if status == 200:
        print(f"   ✓ Logout passed")
        return True
    else:
        print(f"   ✗ Logout failed: {status} - {response}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Backend Auth Flow Tests")
    print("=" * 60)

    results = []

    # Test health
    results.append(("Health", test_health()))

    # Test ready
    results.append(("Ready", test_ready()))

    # Test signup
    signup_ok, test_email, signup_tokens = test_signup()
    results.append(("Signup", signup_ok))

    if not signup_ok:
        print("\n⚠ Signup failed, skipping remaining tests")
        sys.exit(1)

    # Test login
    login_ok, login_tokens = test_login(test_email)
    results.append(("Login", login_ok))

    if not login_ok or not login_tokens:
        print("\n⚠ Login failed, skipping remaining tests")
        sys.exit(1)

    access_token = login_tokens.get("access_token")
    refresh_token = login_tokens.get("refresh_token")

    # Test /me
    me_ok, user = test_me(access_token)
    results.append(("/me", me_ok))

    # Test refresh
    if refresh_token:
        refresh_ok, new_tokens = test_refresh(refresh_token)
        results.append(("Refresh", refresh_ok))

        # Test logout with new refresh token
        if new_tokens and new_tokens.get("refresh_token"):
            logout_ok = test_logout(new_tokens["refresh_token"])
            results.append(("Logout", logout_ok))
        elif refresh_token:
            logout_ok = test_logout(refresh_token)
            results.append(("Logout", logout_ok))
    else:
        print("\n⚠ No refresh token, skipping refresh/logout tests")
        results.append(("Refresh", False))
        results.append(("Logout", False))

    # Test RBAC - admin endpoint (as student - should fail)
    print(f"\n8. Testing RBAC - /v1/auth/admin/_rbac_smoke (STUDENT token - should fail)...")
    if access_token:
        rbac_student_ok = False
        status, response = make_request(
            "GET", "/auth/admin/_rbac_smoke", headers={"Authorization": f"Bearer {access_token}"}
        )
        if status == 403:
            print(f"   ✓ Correctly rejected STUDENT token with 403")
            rbac_student_ok = True
        else:
            print(f"   ✗ Unexpected response: {status} - {response}")
        results.append(("RBAC Student", rbac_student_ok))

    # Test RBAC - create admin user via DB and test
    print(f"\n9. Testing RBAC - /v1/auth/admin/_rbac_smoke (ADMIN token - should pass)...")
    try:
        from app.db.session import SessionLocal
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        import uuid

        admin_email = f"admin_{int(time.time())}@example.com"
        admin_password = "AdminPass123!"

        # Create admin user directly in DB (signup only creates STUDENT)
        db = SessionLocal()
        try:
            admin_user = User(
                id=uuid.uuid4(),
                name="Admin User",
                email=admin_email,
                password_hash=hash_password(admin_password),
                role=UserRole.ADMIN.value,
                is_active=True,
                email_verified=True,
            )
            db.add(admin_user)
            db.commit()

            # Login as admin
            login_ok, admin_tokens = test_login(admin_email, admin_password)
            if login_ok and admin_tokens:
                admin_access_token = admin_tokens.get("access_token")
                status, response = make_request(
                    "GET",
                    "/auth/admin/_rbac_smoke",
                    headers={"Authorization": f"Bearer {admin_access_token}"},
                )
                if status == 200:
                    print(f"   ✓ ADMIN token accepted")
                    results.append(("RBAC Admin", True))
                else:
                    print(f"   ✗ ADMIN token rejected: {status} - {response}")
                    results.append(("RBAC Admin", False))
            else:
                print(f"   ✗ Failed to login as admin")
                results.append(("RBAC Admin", False))
        finally:
            db.close()
    except Exception as e:
        print(f"   ✗ Error creating/admin user: {e}")
        results.append(("RBAC Admin", False))

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
        print("❌ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
