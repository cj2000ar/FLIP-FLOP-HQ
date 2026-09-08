"""
Configuration seams for hp_api.

Production runs under systemd with the process environment as the only
configuration channel. These tests pin the three values that must come
from the environment rather than from defaults baked into the source:
the fencing HMAC secret, the bind address, and the database directory.
"""

import pytest

import hp_api


@pytest.fixture(autouse=True)
def isolated_db_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("FLIPFLOP_DB_PATH", str(tmp_path))
    return tmp_path


class TestHmacSecretFromEnvironment:
    def test_create_app_uses_env_secret(self, monkeypatch):
        monkeypatch.setenv("HP_HMAC_SECRET", "env-provided-secret")

        app = hp_api.create_app()

        assert app.state.hp.hmac_secret == b"env-provided-secret"

    def test_create_app_warns_when_secret_unset(self, monkeypatch, caplog):
        monkeypatch.delenv("HP_HMAC_SECRET", raising=False)

        with caplog.at_level("WARNING"):
            hp_api.create_app()

        assert any("HP_HMAC_SECRET" in r.getMessage() for r in caplog.records)

    def test_explicit_hp_is_respected(self, tmp_path):
        from hp_infra import HPInfrastructure
        hp = HPInfrastructure(db_path=str(tmp_path / "x.db"), hmac_secret="explicit")

        app = hp_api.create_app(hp)

        assert app.state.hp is hp


class TestMainHonoursEnvironment:
    def test_main_binds_to_api_host_and_port(self, monkeypatch):
        monkeypatch.setenv("API_HOST", "127.0.0.1")
        monkeypatch.setenv("API_PORT", "8123")
        calls = {}
        monkeypatch.setattr(hp_api.uvicorn, "run", lambda app, **kw: calls.update(kw))

        hp_api.main()

        assert calls["host"] == "127.0.0.1"
        assert calls["port"] == 8123

    def test_main_defaults_to_all_interfaces_for_containers(self, monkeypatch):
        monkeypatch.delenv("API_HOST", raising=False)
        calls = {}
        monkeypatch.setattr(hp_api.uvicorn, "run", lambda app, **kw: calls.update(kw))

        hp_api.main()

        assert calls["host"] == "0.0.0.0"

    def test_main_puts_database_under_flipflop_db_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr(hp_api.uvicorn, "run", lambda *a, **k: None)

        hp_api.main()

        assert (tmp_path / "hp_infra.db").exists()
