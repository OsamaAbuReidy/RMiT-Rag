from fastapi.testclient import TestClient

from bnm_compliance_assistant.api.main import app


def test_health() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_index_page_serves_ui() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "BNM Compliance Onboarding Assistant" in response.text
    assert "/static/app.js" in response.text


def test_static_assets_are_served() -> None:
    client = TestClient(app)

    css_response = client.get("/static/styles.css")
    js_response = client.get("/static/app.js")

    assert css_response.status_code == 200
    assert js_response.status_code == 200
    assert "results-grid" in css_response.text
    assert "fetch(\"/answer\"" in js_response.text
