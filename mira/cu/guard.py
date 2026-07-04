"""Garde-fou de périmètre du Locator Computer Use (G-2 / G-12) — CODE, pas prompt.

L'agent Gemini décide ses propres actions à partir de contenu web NON fiable
(injection de prompt visuelle, pub, redirection). Une consigne dans le prompt
(« ne quitte pas le site ») n'est donc pas un garde-fou : seul le code en est un.

Périmètre autorisé = une allow-list de hosts. Par défaut la surface de démo locale
uniquement (G-12 : « la démo cible un mock host […], jamais une vraie plateforme »).
Pour un essai hors démo, l'étendre EXPLICITEMENT via MIRA_CU_ALLOWED_HOSTS — c'est
un acte conscient, pas le défaut. Trois verrous s'appuient sur ce module :
  1. entrée      — l'URL de départ doit être allow-listée (sinon on n'ouvre rien) ;
  2. action      — toute action `navigate` hors périmètre est refusée avant le goto ;
  3. après coup  — l'URL courante est re-vérifiée après CHAQUE action (un clic ou une
                   redirection peut sortir du périmètre sans action `navigate`).
"""

from __future__ import annotations

import os
from urllib.parse import urlparse

# Défaut = mock host servi localement par mira/web (G-12). JAMAIS de host public ici.
_DEFAULT_ALLOWED = "localhost,127.0.0.1"


class OutOfScopeError(ValueError):
    """Cible hors du périmètre autorisé (G-2 / G-12). Hérite de ValueError pour être
    captée par les surfaces qui transforment déjà ValueError en event/erreur propre."""


def allowed_hosts() -> frozenset[str]:
    """Allow-list courante, relue à chaque appel (testable, surchargée par l'env)."""
    raw = os.getenv("MIRA_CU_ALLOWED_HOSTS", _DEFAULT_ALLOWED)
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def host_of(url: str) -> str:
    """Host (sans port) d'une URL, en minuscules. Chaîne vide si non parsable."""
    return (urlparse(url).hostname or "").lower()


def is_allowed(url: str) -> bool:
    """True si le host de `url` est dans l'allow-list. Compare le host seul :
    un port ou un chemin ne relâche jamais la frontière."""
    return host_of(url) in allowed_hosts()


def require_allowed(url: str) -> None:
    """Lève OutOfScopeError si `url` sort du périmètre. Point d'application unique."""
    if not is_allowed(url):
        raise OutOfScopeError(
            f"cible hors périmètre démo (G-2/G-12) : {host_of(url) or url!r} — "
            f"hosts autorisés : {', '.join(sorted(allowed_hosts()))} "
            "(étendre via MIRA_CU_ALLOWED_HOSTS)"
        )
