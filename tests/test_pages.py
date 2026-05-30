from fastapi.testclient import TestClient

from main import app


def test_static_pages_render():
    with TestClient(app) as client:
        assert client.get("/").status_code == 200
        assert client.get("/rules").status_code == 200
