"""Integration Tests for FastAPI Endpoints."""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_test_token(email: str = "api_test_user@bugsense.ai") -> str:
    """Helper to ensure user exists and return valid auth token."""
    password = "SecurePassword123!"
    # Try register first
    reg_res = client.post("/api/auth/register", json={"email": email, "password": password})
    if reg_res.status_code == 200:
        return reg_res.json()["access_token"]
    # Otherwise login
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    return login_res.json()["access_token"]


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data


def test_auth_registration_and_login():
    email = "unique_reg_user@bugsense.ai"
    password = "SecurePassword123!"

    # 1. Register
    reg_res = client.post("/api/auth/register", json={"email": email, "password": password})
    assert reg_res.status_code in (200, 400)
    if reg_res.status_code == 200:
        assert "access_token" in reg_res.json()

    # 2. Login
    login_res = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    assert token is not None

    # 3. Profile
    profile_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert profile_res.status_code == 200
    assert profile_res.json()["email"] == email


def test_upload_raw_code_endpoint():
    token = get_test_token()
    code = "def sample(a, b=[]):\n    return a"
    upload_res = client.post(
        "/api/upload",
        headers={"Authorization": f"Bearer {token}"},
        json={"filename": "sample.py", "code": code},
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["filename"] == "sample.py"
    assert "id" in data

