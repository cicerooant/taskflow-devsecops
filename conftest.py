import os
import secrets

import pytest

# Credenciais geradas a cada execução: nada de senha literal no repositório.
ADMIN_PWD = secrets.token_hex(8)
USER_PWD = secrets.token_hex(8)
os.environ.setdefault("SECRET_KEY", secrets.token_hex(16))


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PWD)
    from app import create_app

    app = create_app(
        {"DB_PATH": str(tmp_path / "t.db"), "SESSION_COOKIE_SECURE": False, "TESTING": True}
    )
    return app.test_client()
