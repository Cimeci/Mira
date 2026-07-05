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


@pytest.fixture(autouse=True)
def _locator_mock(monkeypatch):
    """Locator en mode mock pour TOUTE la suite : les tests doivent rester hermétiques
    (aucun navigateur, aucun réseau). Le mode réel ("crawl"/"cu") est le défaut du
    produit — il se vérifie via le chemin de démo end-to-end (dev.sh), pas en pytest."""
    monkeypatch.setenv("MIRA_LOCATOR_MODE", "mock")
