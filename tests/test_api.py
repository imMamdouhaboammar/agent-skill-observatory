from fastapi.testclient import TestClient

from skill_observatory.api import create_app


def test_health_endpoint(tmp_path) -> None:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as client:
        response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_empty_skills_endpoint(tmp_path) -> None:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as client:
        response = client.get("/api/v1/skills")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0


def test_stats_endpoint(tmp_path) -> None:
    app = create_app(database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as client:
        response = client.get("/api/v1/stats")
    assert response.status_code == 200
    assert response.json()["skills"] == 0
