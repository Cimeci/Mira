"""Connexion Supabase (lane L2) — client lazy, jamais requis par les mocks.

Le squelette tourne SANS clés (règle .env.example) : ce module ne lit l'env et ne
crée le client qu'au PREMIER appel de get_client(). Vars manquantes -> RuntimeError
avec la marche à suivre exacte (fail fast, pas de None qui se propage jusqu'à un
bug de démo).

Côté serveur on privilégie SUPABASE_SERVICE_ROLE_KEY (bypasse le RLS — ne JAMAIS
l'exposer au front/navigateur) ; à défaut, repli sur SUPABASE_ANON_KEY.

Usage :
    from mira.db import get_client
    db = get_client()
    db.table("cases").insert({...}).execute()

Smoke test — vérifie URL + clé contre le vrai projet, sans toucher aux tables :
    .venv/bin/python -m mira.db
"""

from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from dotenv import dotenv_values

if TYPE_CHECKING:
    from supabase import Client

_ENV_FILE = ".env.local"

_MISSING_VARS_HINT = (
    "Connexion Supabase impossible : renseigne SUPABASE_URL et "
    "SUPABASE_SERVICE_ROLE_KEY (ou SUPABASE_ANON_KEY) dans .env.local "
    "(valeurs : dashboard Supabase -> Project Settings -> API)."
)


def _env(key: str) -> str | None:
    """Vraie variable d'environnement d'abord (un déploiement Cloud Run/Vercel n'a
    pas de .env.local), puis le fichier — même lecture fichier que mira.cu."""
    return os.environ.get(key) or dotenv_values(_ENV_FILE).get(key) or None


def _credentials() -> tuple[str, str]:
    url = _env("SUPABASE_URL")
    key = _env("SUPABASE_SERVICE_ROLE_KEY") or _env("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError(_MISSING_VARS_HINT)
    return url, key


@lru_cache(maxsize=1)
def get_client() -> Client:
    """Client Supabase partagé (singleton par process).

    Import de `supabase` différé : les mocks et la suite de tests ne paient la
    dépendance que si quelqu'un touche réellement à la DB.
    """
    url, key = _credentials()
    from supabase import create_client

    return create_client(url, key)


def _smoke() -> None:
    """Prouve que l'URL et la clé ouvrent le projet : GET /rest/v1/ doit répondre
    200 (clé invalide -> 401, mauvaise URL -> erreur réseau). N'écrit rien."""
    import httpx

    url, key = _credentials()
    host = urlparse(url).hostname or url
    try:
        resp = httpx.get(
            f"{url.rstrip('/')}/rest/v1/",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            timeout=10,
        )
    except httpx.HTTPError as exc:
        sys.exit(f"❌ {host} injoignable : {exc}")
    if resp.status_code != 200:
        sys.exit(f"❌ {host} répond {resp.status_code} — clé refusée ou projet en pause.")
    get_client()  # le client officiel se construit aussi sur ces credentials
    print(f"✅ Supabase OK — {host} (clé acceptée, client initialisé)")


if __name__ == "__main__":
    _smoke()
