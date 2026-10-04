from fastapi.testclient import TestClient

from yourss.main import create_app
from yourss.schema import AppSettings


def test_api_docs_are_off_by_default() -> None:
    assert AppSettings.model_fields["api_docs_enabled"].default is False

    app = create_app(api_docs=False)
    assert app.docs_url is None
    assert app.redoc_url is None
    assert app.openapi_url is None
    assert not {"/docs", "/redoc", "/openapi.json"} & {getattr(route, "path", None) for route in app.routes}

    # Their addresses are then no page at all
    client = TestClient(app)
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404


def test_api_docs_can_be_enabled() -> None:
    client = TestClient(create_app(api_docs=True))

    resp = client.get("/docs")
    assert resp.status_code == 200
    assert "swagger" in resp.text.lower()

    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "/api/version" in resp.json()["paths"]
