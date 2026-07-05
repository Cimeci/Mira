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

# Défaut verrouillé (G-12) = surface de démo locale uniquement. On OUVRE le web
# entier explicitement avec MIRA_CU_ALLOWED_HOSTS="*" (choix conscient) ; sinon on
# reste sur cette allow-list. JAMAIS de host public codé en dur ici.
_DEFAULT_ALLOWED = "localhost,127.0.0.1"
_OPEN_WEB = "*"


class OutOfScopeError(ValueError):
    """Cible hors du périmètre autorisé (G-2 / G-12). Hérite de ValueError pour être
    captée par les surfaces qui transforment déjà ValueError en event/erreur propre."""


def _raw_allowlist() -> str:
    """Valeur brute de l'allow-list (env), relue à chaque appel — testable, et le
    périmètre peut changer sans redémarrer. Source = os.environ (pas .env.local) :
    c'est une politique de périmètre, pas un secret ; on la pose au shell / dev.sh."""
    return os.getenv("MIRA_CU_ALLOWED_HOSTS", _DEFAULT_ALLOWED)


def is_open_web() -> bool:
    """True si le périmètre est explicitement ouvert au web entier
    (MIRA_CU_ALLOWED_HOSTS="*"). Assouplissement CONSCIENT de G-2/G-12 : le Locator
    peut alors atteindre n'importe quel host — c'est un opt-in, jamais le défaut."""
    return _raw_allowlist().strip() == _OPEN_WEB


def allowed_hosts() -> frozenset[str]:
    """Allow-list de hosts courante. Vide en mode open-web (cf. is_open_web)."""
    raw = _raw_allowlist()
    if raw.strip() == _OPEN_WEB:
        return frozenset()
    return frozenset(h.strip().lower() for h in raw.split(",") if h.strip())


def host_of(url: str) -> str:
    """Host (sans port) d'une URL, en minuscules. Chaîne vide si non parsable."""
    return (urlparse(url).hostname or "").lower()


def is_allowed(url: str) -> bool:
    """En mode open-web ("*"), tout host http(s) valide passe. Sinon, le host de
    `url` doit être dans l'allow-list — comparé seul : ni port ni chemin ne relâchent
    la frontière."""
    if is_open_web():
        return bool(host_of(url))
    return host_of(url) in allowed_hosts()


def require_allowed(url: str) -> None:
    """Lève OutOfScopeError si `url` sort du périmètre. Point d'application unique."""
    if not is_allowed(url):
        raise OutOfScopeError(
            f"cible hors périmètre (G-2/G-12) : {host_of(url) or url!r} — "
            f"hosts autorisés : {', '.join(sorted(allowed_hosts())) or '(aucun)'} "
            "(étendre via MIRA_CU_ALLOWED_HOSTS, ou '*' pour ouvrir le web entier)"
        )
