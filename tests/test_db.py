"""Tests de mira.db : fail-fast lisible sans credentials, priorité env > fichier.

Aucun accès réseau ici — la connectivité réelle se vérifie via
`python -m mira.db` (smoke CLI, chemin de démo).
"""

import pytest

from mira import db

_VARS = ("SUPABASE_URL", "SUPABASE_ANON_KEY", "SUPABASE_SERVICE_ROLE_KEY")


@pytest.fixture(autouse=True)
def _isolated_env(monkeypatch, tmp_path):
    # Coupe les deux sources : os.environ ET .env.local (fichier inexistant).
    for var in _VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(db, "_ENV_FILE", str(tmp_path / "absent.env"))
    db.get_client.cache_clear()
    yield
    db.get_client.cache_clear()


def test_missing_vars_raise_actionable_error():
    with pytest.raises(RuntimeError, match="SUPABASE_URL"):
        db.get_client()


def test_environ_wins_over_env_file(monkeypatch, tmp_path):
    env_file = tmp_path / "file.env"
    env_file.write_text("SUPABASE_URL=https://from-file.supabase.co\n")
    monkeypatch.setattr(db, "_ENV_FILE", str(env_file))
    monkeypatch.setenv("SUPABASE_URL", "https://from-environ.supabase.co")
    assert db._env("SUPABASE_URL") == "https://from-environ.supabase.co"


def test_service_role_preferred_over_anon(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "service")
    assert db._credentials() == ("https://x.supabase.co", "service")
