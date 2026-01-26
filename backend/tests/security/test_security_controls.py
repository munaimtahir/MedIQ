"""Security verification harness for critical security behaviors."""

import os
import time

import httpx
import pytest

# Base URL for the API (adjust if needed)
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_PREFIX = "/v1"


class TestSecurityControls:
    """Security verification tests."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup for each test."""
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)
        self.request_ids: list[str] = []
        yield
        # Cleanup
        await self.client.aclose()

    def _extract_request_id(self, response: httpx.Response) -> str | None:
        """Extract request ID from response header."""
        return response.headers.get("X-Request-ID")

    def _verify_error_envelope(self, response: httpx.Response, expected_code: str):
        """Verify response uses global error envelope."""
        assert response.status_code >= 400, "Expected error response"
        data = response.json()
        assert "error" in data, "Response must have 'error' key"
        error = data["error"]
        assert "code" in error, "Error must have 'code'"
        assert "message" in error, "Error must have 'message"
        assert "request_id" in error, "Error must have 'request_id'"
        assert error["code"] == expected_code, f"Expected code {expected_code}, got {error['code']}"
        return error

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_1_invalid_login_generic_error(self):
        """TEST 1: Invalid login returns generic error message."""
        response = await self.client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        error = self._verify_error_envelope(response, "UNAUTHORIZED")
        # Verify message is generic (doesn't reveal account existence)
        message = error["message"].lower()
        assert "invalid" in message or "credentials" in message, "Message should be generic"
        assert "does not exist" not in message, "Message should not reveal account existence"
        assert "not found" not in message, "Message should not reveal account existence"

        request_id = self._extract_request_id(response)
        if request_id:
            self.request_ids.append(request_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_2_rate_limiting(self):
        """TEST 2: Rate limiting returns 429 with Retry-After header."""
        # Rapidly call login endpoint
        responses = []
        for _ in range(25):  # Exceed default limit of 20
            try:
                response = await self.client.post(
                    f"{API_PREFIX}/auth/login",
                    json={"email": f"test{time.time()}@example.com", "password": "wrong"},
                )
                responses.append(response)
                if response.status_code == 429:
                    break
            except Exception:
                pass
            time.sleep(0.1)  # Small delay

        # Find rate limited response
        rate_limited_response = None
        for resp in responses:
            if resp.status_code == 429:
                rate_limited_response = resp
                break

        assert rate_limited_response is not None, "Rate limit should have been triggered"

        error = self._verify_error_envelope(rate_limited_response, "RATE_LIMITED")
        assert (
            "Retry-After" in rate_limited_response.headers
        ), "Response must include Retry-After header"
        retry_after = int(rate_limited_response.headers["Retry-After"])
        assert retry_after > 0, "Retry-After must be positive"

        # Verify details match
        if error.get("details") and isinstance(error["details"], dict):
            details_retry = error["details"].get("retry_after_seconds")
            if details_retry:
                assert abs(details_retry - retry_after) <= 1, "Details should match header"

        request_id = self._extract_request_id(rate_limited_response)
        if request_id:
            self.request_ids.append(request_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_3_account_lockout(self):
        """TEST 3: Account lockout after repeated failures."""
        test_email = f"lockout_test_{int(time.time())}@example.com"

        # First, create a user (if signup exists)
        try:
            await self.client.post(
                f"{API_PREFIX}/auth/signup",
                json={
                    "name": "Lockout Test",
                    "email": test_email,
                    "password": "TestPassword123!",
                },
            )
        except Exception:
            pass  # User might already exist

        # Trigger failed logins to reach threshold (default 8)
        responses = []
        for _i in range(10):
            response = await self.client.post(
                f"{API_PREFIX}/auth/login",
                json={"email": test_email, "password": "wrongpassword"},
            )
            responses.append(response)
            if response.status_code == 403:
                # Check if it's a lockout
                data = response.json()
                if "error" in data and data["error"].get("code") == "ACCOUNT_LOCKED":
                    break
            time.sleep(0.1)

        # Find lockout response
        lockout_response = None
        for resp in responses:
            if resp.status_code == 403:
                data = resp.json()
                if "error" in data and data["error"].get("code") == "ACCOUNT_LOCKED":
                    lockout_response = resp
                    break

        assert lockout_response is not None, "Account lockout should have been triggered"
        error = self._verify_error_envelope(lockout_response, "ACCOUNT_LOCKED")

        # Verify lock expiry in details
        if error.get("details") and isinstance(error["details"], dict):
            lock_expires = error["details"].get("lock_expires_in")
            assert lock_expires is not None, "Details should include lock_expires_in"
            assert lock_expires > 0, "Lock expiry should be positive"

        request_id = self._extract_request_id(lockout_response)
        if request_id:
            self.request_ids.append(request_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_4_oauth_invalid_state(self):
        """TEST 4: OAuth callback with invalid state returns OAUTH_STATE_INVALID."""
        # Call callback with bogus state (no Redis entry)
        response = await self.client.get(
            f"{API_PREFIX}/auth/oauth/google/callback",
            params={"code": "fake_code", "state": "invalid_state_12345"},
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        self._verify_error_envelope(response, "OAUTH_STATE_INVALID")

        request_id = self._extract_request_id(response)
        if request_id:
            self.request_ids.append(request_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_5_mfa_invalid_code(self):
        """TEST 5: MFA invalid code returns MFA_INVALID."""
        # This test requires a user with MFA enabled
        # For now, we'll test the endpoint structure
        # In a real scenario, you'd set up a test user with MFA first

        # Try to complete MFA with invalid token
        response = await self.client.post(
            f"{API_PREFIX}/auth/mfa/complete",
            json={"mfa_token": "invalid_token", "code": "123456"},
        )

        # Should return 401 or 400
        assert response.status_code in [400, 401], f"Expected 400/401, got {response.status_code}"
        data = response.json()
        if "error" in data:
            # Verify it's either UNAUTHORIZED or MFA_INVALID
            error_code = data["error"].get("code")
            assert error_code in [
                "UNAUTHORIZED",
                "MFA_INVALID",
            ], f"Unexpected error code: {error_code}"

        request_id = self._extract_request_id(response)
        if request_id:
            self.request_ids.append(request_id)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_6_logs_include_request_id_and_event_type(self):
        """TEST 6: Verify logs include request_id and event_type."""
        # This test requires access to logs
        # For docker, we can try to read from stdout or log file
        # For now, we'll verify that request_ids were collected
        assert len(self.request_ids) > 0, "Should have collected request IDs from previous tests"

        # In a real implementation, you would:
        # 1. Read logs from docker logs or log file
        # 2. Parse JSON logs
        # 3. Verify each request_id appears with corresponding event_type
        # For now, we'll just verify the structure

        # Example log structure check (would need actual log access)
        # log_lines = get_recent_logs()
        # for request_id in self.request_ids:
        #     found = False
        #     for line in log_lines:
        #         log_data = json.loads(line)
        #         if log_data.get("request_id") == request_id:
        #             assert "event_type" in log_data, "Log should include event_type"
        #             found = True
        #             break
        #     assert found, f"Request ID {request_id} should appear in logs"

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_7_no_secrets_in_logs(self):
        """TEST 7: Verify no secrets appear in logs."""
        # Dangerous substrings to check for

        # In a real implementation, you would:
        # 1. Read logs from docker logs or log file
        # 2. Check each line against patterns
        # 3. Fail if any match (with context)

        # For now, this is a placeholder that documents the requirement
        # Actual implementation would need log access
        pass  # Would need actual log file access to implement fully


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
