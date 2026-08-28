"""Tests for Error Handling Envelopes and Exceptions."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_test_token(email: str = "err_test_user@bugsense.ai") -> str:
    """Helper to ensure user exists and return valid auth token."""
    password = "SecurePassword123!"
    reg_res = client.post("/api/auth/register", json={"email": email, "password": password})
    if reg_res.status_code == 200:
        return reg_res.json()["access_token"]
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    return login_res.json()["access_token"]


def test_error_envelope_format_on_not_found():
    res = client.get("/api/reports/999999", headers={"Authorization": "Bearer invalid"})
    assert res.status_code in (401, 404)
    data = res.json()
    assert "error" in data
    assert "code" in data["error"]
    assert "message" in data["error"]


def test_syntax_error_validation_envelope():
    token = get_test_token()
    # Upload bad syntax code
    bad_code = "def broken(\n    return"
    res = client.post(
        "/api/upload",
        headers={"Authorization": f"Bearer {token}"},
        json={"filename": "broken.py", "code": bad_code},
    )
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "CODE_SYNTAX_ERROR"

