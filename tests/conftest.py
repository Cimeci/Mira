"""Fixtures communes.

DB coupée pour TOUTE la suite : un dev avec un .env.local rempli ne doit pas
écrire dans le vrai Supabase en lançant pytest (la suite doit rester hermétique,
sans réseau). La persistance réelle se vérifie via `python -m mira.db` et le
chemin de démo end-to-end.
"""

import pytest

from mira import db


@pytest.fixture(autouse=True)
def _no_db(monkeypatch):
    monkeypatch.setattr(db, "is_configured", lambda: False)
