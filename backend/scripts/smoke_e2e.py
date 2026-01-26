"""Smoke test script for end-to-end API testing.

Runs basic API calls against local docker compose stack.
"""

import asyncio
import sys
from uuid import uuid4

import httpx


async def smoke_test():
    """Run smoke tests against local API."""
    base_url = "http://localhost:8000/api/v1"
    client = httpx.AsyncClient(base_url=base_url, timeout=30.0)

    print("Running smoke tests...")

    try:
        # 1. Health check
        print("1. Testing health endpoint...")
        response = await client.get("/health")
        assert response.status_code == 200
        print("   ✓ Health check passed")

        # 2. Test auth (if endpoints exist)
        # This would test signup/login flow

        # 3. Test session creation
        # This would test creating a session, answering, submitting

        print("\nAll smoke tests passed!")

    except Exception as e:
        print(f"\nSmoke test failed: {e}")
        sys.exit(1)
    finally:
        await client.aclose()


if __name__ == "__main__":
    asyncio.run(smoke_test())
