"""Garde-fou de périmètre du Locator CU (G-2 / G-12) — ces fonctions SONT
l'application des guardrails, elles ne peuvent pas rester sans test.

On couvre les trois points d'application de mira.cu.guard :
  1. l'allow-list elle-même (défaut démo, extension explicite par env) ;
  2. l'entrée `_validate_url` (aucun crawl sur une cible hors périmètre) ;
  3. l'action `navigate` (refus AVANT le goto d'une URL décidée par le modèle).
"""

import asyncio

import pytest

from mira.cu import guard
from mira.cu.actions import exec_action
from mira.cu.scraper import _validate_url

# --- 1. Allow-list -----------------------------------------------------------

def test_default_allowlist_is_local_only():
    """Par défaut (G-12) : seule la surface de démo locale est atteignable."""
    assert guard.is_allowed("http://127.0.0.1:8000/mockhost/gallery.html")
    assert guard.is_allowed("http://localhost:8000/mockhost/photo/1.html")
    assert not guard.is_allowed("https://x.com/victim")
    assert not guard.is_allowed("https://evil-mirror.example/leak.jpg")


def test_host_compared_not_path_or_port():
    """Un chemin ou un port ne relâche jamais la frontière : on compare le host seul."""
    assert guard.host_of("https://EVIL.example:443/127.0.0.1") == "evil.example"
    assert not guard.is_allowed("https://evil.example/?redir=127.0.0.1")


def test_allowlist_extended_only_by_explicit_env(monkeypatch):
    """Étendre le périmètre est un acte conscient (MIRA_CU_ALLOWED_HOSTS), pas le défaut."""
    assert not guard.is_allowed("https://mock-host.local/target")
    monkeypatch.setenv("MIRA_CU_ALLOWED_HOSTS", "mock-host.local, other.local")
    assert guard.is_allowed("https://mock-host.local/target")
    assert guard.is_allowed("https://other.local/x")
    assert not guard.is_allowed("http://127.0.0.1/x")  # remplacé, pas ajouté


def test_require_allowed_raises_out_of_scope():
    with pytest.raises(guard.OutOfScopeError):
        guard.require_allowed("https://x.com/victim")
    # Hérite de ValueError -> capté par les surfaces qui gèrent déjà ValueError.
    assert issubclass(guard.OutOfScopeError, ValueError)


# --- 2. Entrée : _validate_url ----------------------------------------------

def test_validate_url_rejects_out_of_scope_host():
    _validate_url("http://127.0.0.1:8000/mockhost/gallery.html")  # ne lève pas
    with pytest.raises(ValueError):
        _validate_url("https://vrai-site.example/x")
    with pytest.raises(ValueError):
        _validate_url("ftp://127.0.0.1/x")  # schéma non http(s)


# --- 3. Action navigate : refus avant le goto -------------------------------

class _FakePage:
    """Stub minimal : enregistre si goto a été appelé, sans vrai navigateur."""

    def __init__(self, url: str = "http://127.0.0.1:8000/mockhost/gallery.html"):
        self.url = url
        self.goto_calls: list[str] = []

    async def goto(self, url: str, **_kwargs) -> None:
        self.goto_calls.append(url)
        self.url = url


def test_navigate_out_of_scope_blocked_before_goto():
    page = _FakePage()
    result = asyncio.run(exec_action(page, "navigate", {"url": "https://x.com/victim"}))
    assert result["status"] == "blocked_out_of_scope"
    assert page.goto_calls == []  # le site tiers n'a JAMAIS été chargé


def test_navigate_in_scope_allowed():
    page = _FakePage()
    target = "http://127.0.0.1:8000/mockhost/photo/2.html"
    result = asyncio.run(exec_action(page, "navigate", {"url": target}))
    assert result["status"] == "ok"
    assert page.goto_calls == [target]
