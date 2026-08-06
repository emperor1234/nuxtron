from backend.fastapi.app.main import app


def test_main_app_entrypoint_exposes_fastapi_app() -> None:
    assert app is not None
    assert hasattr(app, "routes")
    assert len(app.routes) > 0
