"""Tests for developers router — API access request."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

VALID_PAYLOAD = {
    "name": "Ana Silva",
    "email": "ana@empresa.com",
    "company": "TechCo Brasil",
    "role": "CTO",
    "use_case": "Integrar dados de startups LATAM no nosso dashboard interno de market intelligence.",
}


def test_request_access_success():
    """Test successful API access request returns 201."""
    response = client.post("/api/developers/request-access", json=VALID_PAYLOAD)

    assert response.status_code == 201
    data = response.json()
    assert "message" in data
    assert "contato" in data["message"].lower()


def test_request_access_missing_fields():
    """Test that missing required fields return 422."""
    # Missing use_case
    payload = {
        "name": "Ana Silva",
        "email": "ana@empresa.com",
        "company": "TechCo",
        "role": "CTO",
    }
    response = client.post("/api/developers/request-access", json=payload)
    assert response.status_code == 422


def test_request_access_invalid_email():
    """Test that invalid email returns 400."""
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    response = client.post("/api/developers/request-access", json=payload)
    assert response.status_code == 400
    assert "inválido" in response.json()["detail"].lower()


def test_request_access_empty_body():
    """Test that empty body returns 422."""
    response = client.post("/api/developers/request-access", json={})
    assert response.status_code == 422


def test_request_access_use_case_too_short():
    """Test that use_case shorter than 10 chars returns 422."""
    payload = {**VALID_PAYLOAD, "use_case": "short"}
    response = client.post("/api/developers/request-access", json=payload)
    assert response.status_code == 422


def test_request_access_name_too_short():
    """Test that name shorter than 2 chars returns 422."""
    payload = {**VALID_PAYLOAD, "name": "A"}
    response = client.post("/api/developers/request-access", json=payload)
    assert response.status_code == 422


@patch("apps.api.routers.developers.send_api_access_notification")
def test_email_notification_called(mock_send):
    """Test that email notification is triggered on success."""
    mock_send.return_value = True

    response = client.post("/api/developers/request-access", json=VALID_PAYLOAD)
    assert response.status_code == 201

    # BackgroundTasks are executed synchronously in TestClient
    mock_send.assert_called_once_with(
        name="Ana Silva",
        email="ana@empresa.com",
        company="TechCo Brasil",
        role="CTO",
        use_case="Integrar dados de startups LATAM no nosso dashboard interno de market intelligence.",
    )
