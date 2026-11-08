import pytest

from app.config import settings
from app.main import startup


def test_production_startup_fails_closed_until_verified_auth(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "app_secret_key", "production-test-secret-" + "x" * 40)
    monkeypatch.setattr(settings, "upload_dir", tmp_path / "uploads")

    with pytest.raises(RuntimeError, match="no real email/phone OTP"):
        startup()

    assert not (tmp_path / "uploads").exists()
