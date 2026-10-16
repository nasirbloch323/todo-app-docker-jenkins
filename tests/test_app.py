import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.mark.parametrize("path", ["/", "/services", "/contact", "/health"])
def test_pages_load(client, path):
    assert client.get(path).status_code == 200


def test_404(client):
    assert client.get("/nope").status_code == 404


def test_contact_valid(client):
    r = client.post("/contact", data={"name": "Ali", "email": "ali@x.com", "message": "I need a website please"}, follow_redirects=True)
    assert b"we received your message" in r.data


def test_contact_invalid(client):
    r = client.post("/contact", data={"name": "", "email": "bad", "message": "hi"})
    assert r.status_code == 400
