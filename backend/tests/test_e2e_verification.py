"""Comprehensive End-to-End API and UI Contract Verification for BugSense AI Fixes."""
import io
import zipfile
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient):
    # Register/login test user
    login_res = client.post(
        "/api/auth/login",
        json={"email": "demo@bugsense.ai", "password": "password123"},
    )
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
    else:
        reg_res = client.post(
            "/api/auth/register",
            json={"email": "demo@bugsense.ai", "password": "password123"},
        )
        token = reg_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_e2e_language_detection_and_analysis(client: TestClient, auth_headers: dict):
    """E2E Bug 1 Verification:
    Submit valid Python code with language='Python' and filename='SyntaxErrorDemo.java'.
    Verify zero Java syntax checker errors are returned.
    """
    python_code = """def calculate_average(numbers):
    if not numbers:
        return 0
    total = sum(numbers)
    return total / len(numbers)

print(calculate_average([10, 20, 30]))
"""
    # 1. Upload
    upload_res = client.post(
        "/api/upload",
        json={
            "filename": "SyntaxErrorDemo.java",
            "code": python_code,
            "language": "Python",
        },
        headers=auth_headers,
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    submission_id = data["id"]
    assert data["language"] == "Python"
    assert data["filename"] == "SyntaxErrorDemo.java"

    # 2. Run analysis
    analysis_res = client.post(
        f"/api/analysis/{submission_id}/run",
        headers=auth_headers,
    )
    assert analysis_res.status_code == 200
    analysis_data = analysis_res.json()

    # 3. Fetch bugs
    bugs_res = client.get(f"/api/bugs/{submission_id}", headers=auth_headers)
    assert bugs_res.status_code == 200
    bugs_data = bugs_res.json()

    # Verify no Java syntax false-positives
    for b in bugs_data.get("bugs", []):
        assert "JAVA-SYNTAX" not in b.get("rule_id", "")
        assert "java_syntax_checker" not in b.get("tool", "")
        assert "missing semicolon" not in b.get("message", "").lower()


def test_e2e_zip_upload_and_extraction(client: TestClient, auth_headers: dict):
    """E2E Bug 2 Verification:
    Upload a multi-file ZIP archive.
    Verify all files are extracted, returned in response, with raw_code populated.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("service_a.py", "def service_a():\n    return 'service_a'\n")
        zf.writestr("service_b.js", "function serviceB() { return 'service_b'; }\n")
        zf.writestr("Main.java", "public class Main { public static void main(String[] args) {} }\n")

    zip_bytes = zip_buffer.getvalue()

    response = client.post(
        "/api/upload/file",
        files={"file": ("project_bundle.zip", zip_bytes, "application/zip")},
        headers=auth_headers,
    )
    assert response.status_code == 200
    files_data = response.json()
    assert len(files_data) == 3

    filenames = [f["filename"] for f in files_data]
    assert "service_a.py" in filenames
    assert "service_b.js" in filenames
    assert "Main.java" in filenames

    for f in files_data:
        assert len(f["raw_code"].strip()) > 0
        assert f["language"] in ["Python", "JavaScript", "Java"]


def test_e2e_submissions_history_schema(client: TestClient, auth_headers: dict):
    """E2E Bug 3 Verification:
    Verify /upload/history endpoint provides data for Date-only frontend rendering
    and that database model timestamps remain intact.
    """
    res = client.get("/api/upload/history", headers=auth_headers)
    assert res.status_code == 200
    history = res.json()
    assert isinstance(history, list)
    if len(history) > 0:
        first = history[0]
        assert "uploaded_at" in first
        assert "filename" in first
        assert "language" in first
