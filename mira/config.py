"""Config via variables d'environnement (.env.local, jamais commité)."""

from __future__ import annotations

import os

# Seuil au-dessus duquel un contenu est considéré comme deepfake (spec §8.3).
DEEPFAKE_SCORE_THRESHOLD: float = float(os.getenv("DEEPFAKE_SCORE_THRESHOLD", "0.85"))

# Rétention des preuves (jours) avant purge automatique (RGPD, limitation de conservation).
EVIDENCE_RETENTION_DAYS: int = int(os.getenv("EVIDENCE_RETENTION_DAYS", "90"))
