from datetime import date, timedelta

import pytest

from app import create_app, init_db


def future(days=3):
    return (date.today() + timedelta(days=days)).isoformat()


def valid(**over):
    data = {"name": "Ayesha Khan", "phone": "0300 1234567", "department": "general",
            "date": future(), "note": "Fever for two days"}
    data.update(over)
    return data


@pytest.fixture
def client():
    app = create_app("sqlite://")
    init_db(app.config["ENGINE"])
    app.config["TESTING"] = True
    return app.test_client()


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.get_json()["database"] == "up"


def test_health_degraded_when_db_down(client, monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db down")
    monkeypatch.setattr(client.application.config["ENGINE"], "connect", boom)
    r = client.get("/api/health")
    assert r.status_code == 503 and r.get_json()["database"] == "down"


def test_departments_seeded(client):
    data = client.get("/api/departments").get_json()
    assert len(data) == 6
    assert {"slug", "name", "description", "opd_hours"} <= set(data[0])


def test_notices_newest_first(client):
    data = client.get("/api/notices").get_json()
    assert len(data) == 4
    dates = [n["published_at"] for n in data]
    assert dates == sorted(dates, reverse=True)


def test_init_db_is_idempotent(client):
    init_db(client.application.config["ENGINE"])
    assert len(client.get("/api/departments").get_json()) == 6
    assert len(client.get("/api/notices").get_json()) == 4


def test_book_and_stats(client):
    r = client.post("/api/appointments", json=valid())
    assert r.status_code == 201
    body = r.get_json()
    assert body["reference"] == "SH-000001" and body["status"] == "Pending"
    assert client.get("/api/stats").get_json() == {"departments": 6, "appointments": 1}


@pytest.mark.parametrize("over,field", [
    ({"name": ""}, "name"),
    ({"phone": "abc"}, "phone"),
    ({"phone": "123"}, "phone"),
    ({"department": "nope"}, "department"),
    ({"date": (date.today() - timedelta(days=1)).isoformat()}, "date"),
    ({"date": future(400)}, "date"),
    ({"date": "not-a-date"}, "date"),
    ({"note": "x" * 501}, "note"),
])
def test_book_invalid(client, over, field):
    r = client.post("/api/appointments", json=valid(**over))
    assert r.status_code == 400 and field in r.get_json()["errors"]


def test_book_requires_json(client):
    assert client.post("/api/appointments", data="x=1").status_code == 400


def test_lookup_success_any_phone_format(client):
    ref = client.post("/api/appointments", json=valid()).get_json()["reference"]
    r = client.get(f"/api/appointments/{ref.lower()}", query_string={"phone": "03001234567"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["department"] == "General Medicine" and body["status"] == "Pending"


def test_lookup_wrong_phone_or_ref_is_404(client):
    ref = client.post("/api/appointments", json=valid()).get_json()["reference"]
    assert client.get(f"/api/appointments/{ref}", query_string={"phone": "03009999999"}).status_code == 404
    assert client.get(f"/api/appointments/{ref}").status_code == 404
    assert client.get("/api/appointments/SH-999999", query_string={"phone": "03001234567"}).status_code == 404


def test_unknown_route_is_json_404(client):
    r = client.get("/api/nope")
    assert r.status_code == 404 and r.get_json()["error"] == "Not found"
