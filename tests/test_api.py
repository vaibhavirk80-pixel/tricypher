
import pytest
from fastapi.testclient import TestClient

from src.tricypher.api import app


client = TestClient(app)


def test_home_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protect_endpoint():
    original = (
        "My name is Shweta Desai "
        "and my email is shweta@example.com"
    )

    response = client.post(
        "/v1/protect",
        json={"text": original},
    )

    assert response.status_code == 200

    data = response.json()

    assert "protected_text" in data
    assert "detected_count" in data
    assert "detected_types" in data
    assert "token_map" in data

    assert "Shweta Desai" not in data["protected_text"]
    assert "shweta@example.com" not in data["protected_text"]


def test_restore_endpoint():
    original = "My name is Shweta Desai"

    protected_response = client.post(
        "/v1/protect",
        json={"text": original},
    )

    assert protected_response.status_code == 200

    protected_text = protected_response.json()["protected_text"]

    restore_response = client.post(
        "/v1/restore",
        json={"protected_text": protected_text},
    )

    assert restore_response.status_code == 200
    assert restore_response.json()["restored_text"] == original


def test_protect_empty_text():
    response = client.post(
        "/v1/protect",
        json={"text": ""},
    )

    assert response.status_code == 422


def test_protect_missing_text():
    response = client.post(
        "/v1/protect",
        json={},
    )

    assert response.status_code == 422
