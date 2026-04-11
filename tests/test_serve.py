"""Tests for the napoleon server, run with the uv tool's Python."""
import json
import sys
import os

# Use the same Python/packages as the napoleon tool
TOOL_PYTHON = os.path.expanduser("~/.local/share/uv/tools/napoleon/bin/python3")


def _run_snippet(code):
    """Run a Python snippet in the napoleon tool's venv and return stdout."""
    import subprocess
    result = subprocess.run(
        [TOOL_PYTHON, "-c", code],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode != 0:
        print("STDERR:", result.stderr)
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def test_imports():
    out, err, rc = _run_snippet("""
import websockets
print(websockets.__version__)
from websockets.http11 import Response
from websockets.datastructures import Headers
print("imports OK")
""")
    assert rc == 0, f"Import failed: {err}"
    assert "imports OK" in out


def test_response_construction():
    out, err, rc = _run_snippet("""
import json
from websockets.http11 import Response
from websockets.datastructures import Headers

body = json.dumps({"hello": "world"}).encode()
r = Response(200, "OK", Headers({
    "Content-Type": "application/json",
    "Content-Length": str(len(body)),
}), body)
print("status:", r.status_code)
print("body:", r.body)
""")
    assert rc == 0, f"Response construction failed: {err}"
    assert "status: 200" in out


def test_json_response_function():
    out, err, rc = _run_snippet("""
import json, sys
sys.path.insert(0, "src")
from napoleon.serve import json_response
r = json_response({"test": True})
print("status:", r.status_code)
print("body:", r.body)
""")
    assert rc == 0, f"json_response failed: {err}"
    assert "status: 200" in out


def test_handle_http_errors_endpoint():
    out, err, rc = _run_snippet("""
import json, sys
sys.path.insert(0, "src")
from napoleon.serve import handle_http
r = handle_http("/api/errors", {})
print("status:", r.status_code)
body = json.loads(r.body)
print("type:", type(body).__name__)
""")
    assert rc == 0, f"handle_http /api/errors failed: {err}"
    assert "status: 200" in out
    assert "type: list" in out


def test_handle_http_repos_endpoint():
    out, err, rc = _run_snippet("""
import json, sys
sys.path.insert(0, "src")
from napoleon.serve import handle_http
r = handle_http("/api/repos", {})
print("status:", r.status_code)
body = json.loads(r.body)
print("type:", type(body).__name__)
print("count:", len(body))
""")
    assert rc == 0, f"handle_http /api/repos failed: {err}"
    assert "status: 200" in out
    assert "type: list" in out


def test_handle_http_ws_returns_none():
    out, err, rc = _run_snippet("""
import sys
sys.path.insert(0, "src")
from napoleon.serve import handle_http
r = handle_http("/api/ws", {})
print("result:", r)
""")
    assert rc == 0, f"handle_http /api/ws failed: {err}"
    assert "result: None" in out


def test_process_request():
    out, err, rc = _run_snippet("""
import asyncio, json, sys
sys.path.insert(0, "src")
from napoleon.serve import process_request

# Mock connection and request
class FakeRequest:
    path = "/api/repos"
    method = "GET"

async def run():
    r = await process_request(None, FakeRequest())
    print("status:", r.status_code)
    body = json.loads(r.body)
    print("type:", type(body).__name__)

asyncio.run(run())
""")
    assert rc == 0, f"process_request failed: {err}"
    assert "status: 200" in out


if __name__ == "__main__":
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        print(f"  {t.__name__}...", end=" ")
        try:
            t()
            print("OK")
        except AssertionError as e:
            print(f"FAIL: {e}")
        except Exception as e:
            print(f"ERROR: {e}")
