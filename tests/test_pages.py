from fastapi.testclient import TestClient

from main import app


def test_static_pages_render():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/rules").status_code == 200


def test_golden_evaluation_api_returns_metrics():
    with TestClient(app) as client:
        response = client.get("/api/evaluation/golden")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_cases"] == 8
    assert payload["precision"] == 1.0
    assert payload["recall"] == 1.0
    assert payload["false_positive_count"] == 0
    assert payload["false_negative_count"] == 0
