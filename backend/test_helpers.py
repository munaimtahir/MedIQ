#!/usr/bin/env python3
"""
Shared test utilities for backend tests.
Provides retry logic, health checks, and Docker network awareness.
"""

import json
import os
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def is_running_in_docker() -> bool:
    """Check if running inside a Docker container."""
    # Check for .dockerenv file
    if os.path.exists("/.dockerenv"):
        return True
    # Check cgroup (Linux containers)
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass
    # Check hostname matches container naming
    hostname = socket.gethostname()
    return len(hostname) == 12 and hostname.isalnum()


def get_service_url(service: str, port: int) -> str:
    """
    Get the correct URL for a service based on execution context.
    
    When running inside Docker, use service names (backend:8000, frontend:3000).
    When running on host, use localhost.
    
    Args:
        service: Service name (backend, frontend)
        port: Service port
        
    Returns:
        Full URL with protocol
    """
    if is_running_in_docker():
        return f"http://{service}:{port}"
    else:
        return f"http://localhost:{port}"


# Default URLs based on context
def get_backend_url() -> str:
    """Get backend API URL."""
    return os.environ.get("BACKEND_URL", get_service_url("backend", 8000))


def get_frontend_url() -> str:
    """Get frontend URL."""
    return os.environ.get("FRONTEND_URL", get_service_url("frontend", 3000))


def wait_for_service(
    url: str,
    timeout: int = 60,
    interval: float = 2.0,
    expected_status: int | None = None,
) -> bool:
    """
    Wait for a service to be ready.
    
    Args:
        url: URL to check (e.g., http://backend:8000/v1/health)
        timeout: Maximum wait time in seconds
        interval: Time between checks in seconds
        expected_status: Expected HTTP status (None = any 2xx/3xx)
        
    Returns:
        True if service is ready, False if timeout
    """
    start_time = time.time()
    last_error = None
    
    print(f"Waiting for {url} (timeout: {timeout}s)...")
    
    while time.time() - start_time < timeout:
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=5) as response:
                status = response.getcode()
                if expected_status is None:
                    if 200 <= status < 400:
                        print(f"  ✓ Service ready (status: {status})")
                        return True
                elif status == expected_status:
                    print(f"  ✓ Service ready (status: {status})")
                    return True
        except HTTPError as e:
            last_error = f"HTTP {e.code}"
            if expected_status and e.code == expected_status:
                print(f"  ✓ Service ready (status: {e.code})")
                return True
        except URLError as e:
            last_error = str(e.reason)
        except Exception as e:
            last_error = str(e)
        
        elapsed = int(time.time() - start_time)
        print(f"  ... waiting ({elapsed}s, last: {last_error})")
        time.sleep(interval)
    
    print(f"  ✗ Timeout after {timeout}s (last: {last_error})")
    return False


def make_request_with_retry(
    method: str,
    url: str,
    data: dict | None = None,
    headers: dict | None = None,
    max_retries: int = 3,
    timeout: int = 30,
    retry_on_5xx: bool = True,
) -> tuple[int | None, dict, dict]:
    """
    Make HTTP request with retry logic for transient failures.
    
    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full URL
        data: JSON body (will be encoded)
        headers: Additional headers
        max_retries: Number of retries for transient errors
        timeout: Request timeout in seconds
        retry_on_5xx: Whether to retry on 5xx errors
        
    Returns:
        Tuple of (status_code, response_body, response_headers)
        status_code is None on connection failure
    """
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    
    body_bytes = json.dumps(data).encode() if data else None
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            req = Request(
                url,
                data=body_bytes,
                headers=req_headers,
                method=method,
            )
            with urlopen(req, timeout=timeout) as response:
                status = response.getcode()
                resp_headers = dict(response.headers.items())
                try:
                    body = json.loads(response.read().decode())
                except json.JSONDecodeError:
                    body = {}
                return status, body, resp_headers
                
        except HTTPError as e:
            status = e.code
            resp_headers = dict(e.headers.items()) if e.headers else {}
            try:
                body = json.loads(e.read().decode())
            except (json.JSONDecodeError, AttributeError):
                body = {"error": {"code": "HTTP_ERROR", "message": str(e)}}
            
            # Don't retry on 4xx errors (client errors)
            if 400 <= status < 500:
                return status, body, resp_headers
            
            # Retry on 5xx if enabled
            if retry_on_5xx and 500 <= status < 600 and attempt < max_retries:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s (HTTP {status})")
                time.sleep(wait_time)
                continue
            
            return status, body, resp_headers
            
        except URLError as e:
            last_error = str(e.reason)
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s ({last_error})")
                time.sleep(wait_time)
                continue
            return None, {"error": {"code": "CONNECTION_ERROR", "message": last_error}}, {}
            
        except Exception as e:
            last_error = str(e)
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"  Retry {attempt + 1}/{max_retries} after {wait_time}s ({last_error})")
                time.sleep(wait_time)
                continue
            return None, {"error": {"code": "UNKNOWN_ERROR", "message": last_error}}, {}
    
    return None, {"error": {"code": "MAX_RETRIES", "message": f"Failed after {max_retries} retries"}}, {}


def check_docker_network() -> dict:
    """
    Check Docker network connectivity.
    
    Returns:
        Dict with connectivity status for each service
    """
    results = {
        "running_in_docker": is_running_in_docker(),
        "services": {},
    }
    
    services = [
        ("backend", 8000, "/v1/health"),
        ("frontend", 3000, "/"),
    ]
    
    for service, port, path in services:
        url = get_service_url(service, port) + path
        try:
            req = Request(url, method="GET")
            with urlopen(req, timeout=5) as response:
                results["services"][service] = {
                    "status": "ok",
                    "url": url,
                    "http_status": response.getcode(),
                }
        except HTTPError as e:
            results["services"][service] = {
                "status": "ok",  # Service responded
                "url": url,
                "http_status": e.code,
            }
        except URLError as e:
            results["services"][service] = {
                "status": "error",
                "url": url,
                "error": str(e.reason),
            }
        except Exception as e:
            results["services"][service] = {
                "status": "error",
                "url": url,
                "error": str(e),
            }
    
    return results


def print_test_header(title: str):
    """Print a formatted test header."""
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()


def print_test_summary(results: list[tuple[str, bool]]) -> int:
    """
    Print test summary and return exit code.
    
    Args:
        results: List of (test_name, passed) tuples
        
    Returns:
        0 if all passed, 1 if any failed
    """
    print()
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"{status} - {name}")
    
    print()
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    # Self-test
    print_test_header("Test Helpers Self-Test")
    
    print("Environment Detection:")
    print(f"  Running in Docker: {is_running_in_docker()}")
    print(f"  Backend URL: {get_backend_url()}")
    print(f"  Frontend URL: {get_frontend_url()}")
    print()
    
    print("Docker Network Check:")
    network_status = check_docker_network()
    print(f"  Running in Docker: {network_status['running_in_docker']}")
    for service, status in network_status["services"].items():
        if status["status"] == "ok":
            print(f"  {service}: ✓ {status['url']} (HTTP {status['http_status']})")
        else:
            print(f"  {service}: ✗ {status['url']} ({status['error']})")
