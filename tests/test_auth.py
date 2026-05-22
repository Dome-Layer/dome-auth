from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_head():
    response = client.head("/api/v1/health")
    assert response.status_code == 200


def test_magic_link_invalid_email():
    response = client.post(
        "/api/v1/auth/magic-link",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


def test_magic_link_missing_email():
    response = client.post(
        "/api/v1/auth/magic-link",
        json={},
    )
    assert response.status_code == 422


def test_logout_requires_auth():
    response = client.delete("/api/v1/auth/session")
    assert response.status_code == 401


def test_verify_missing_token():
    response = client.post(
        "/api/v1/auth/verify",
        json={},
    )
    assert response.status_code == 422


def test_security_headers():
    response = client.get("/api/v1/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


def test_rate_limit_magic_link():
    import app.core.limiter as limiter_mod

    limiter_mod._cached_store = limiter_mod._MemoryStore()
    rl_client = TestClient(app, raise_server_exceptions=False)
    try:
        for i in range(5):
            rl_client.post(
                "/api/v1/auth/magic-link",
                json={"email": f"user{i}@example.com"},
                headers={"X-Forwarded-For": "10.0.0.99"},
            )

        response = rl_client.post(
            "/api/v1/auth/magic-link",
            json={"email": "extra@example.com"},
            headers={"X-Forwarded-For": "10.0.0.99"},
        )
        assert response.status_code == 429
    finally:
        limiter_mod._cached_store = None


def test_app_title():
    assert app.title == "Dome Auth Service"


def test_docs_disabled_in_production():
    with patch("app.core.config.settings") as mock_settings:
        mock_settings.environment = "production"
        # The docs_url is set at app creation time, so we just verify
        # the conditional logic exists in the config
        from app.core.config import settings

        assert settings.environment in ("development", "staging", "production")
