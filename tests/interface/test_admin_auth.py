from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from briefing.interface.admin.auth import build_admin_auth_dependency


def _app():
    require = build_admin_auth_dependency("u", "p")
    app = FastAPI()

    @app.get("/admin/ping")
    def ping(_=Depends(require)):
        return {"ok": True}

    return app


def test_unauthenticated_returns_401():
    c = TestClient(_app())
    assert c.get("/admin/ping").status_code == 401


def test_wrong_credentials_returns_401():
    c = TestClient(_app())
    assert c.get("/admin/ping", auth=("u", "wrong")).status_code == 401


def test_correct_credentials_passes():
    c = TestClient(_app())
    r = c.get("/admin/ping", auth=("u", "p"))
    assert r.status_code == 200 and r.json() == {"ok": True}
