"""Config via variables d'environnement (.env.local, jamais commité)."""

from __future__ import annotations

import os

# Seuil au-dessus duquel un contenu est considéré comme deepfake (spec §8.3).
DEEPFAKE_SCORE_THRESHOLD: float = float(os.getenv("DEEPFAKE_SCORE_THRESHOLD", "0.85"))

# Rétention des preuves (jours) avant purge automatique (RGPD, limitation de conservation).
EVIDENCE_RETENTION_DAYS: int = int(os.getenv("EVIDENCE_RETENTION_DAYS", "90"))

# Valeurs env considérées comme « désactivé » pour un flag booléen.
_FALSY = {"", "0", "false", "no"}


def _confirm_timeout_s() -> float:
    """Timeout du gate de confirmation victime (G-7), en secondes — fail-closed.

    En mode démo (MIRA_DEMO_MODE truthy), plancher à 900 s : le présentateur laisse
    la notice à l'écran pendant le beat 2, le gate ne doit PAS s'auto-annuler.
    """
    timeout = float(os.getenv("MIRA_CONFIRM_TIMEOUT_S", "120"))
    if os.getenv("MIRA_DEMO_MODE", "").strip().lower() not in _FALSY:
        timeout = max(timeout, 900.0)
    return timeout


CONFIRM_TIMEOUT_S: float = _confirm_timeout_s()
