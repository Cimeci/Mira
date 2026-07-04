"""Stage 2 — L'Analyzer. Pré-check mineur, vérification forensique, preuve minimale.

Lane L2. Le vrai : API CV (Sightengine) pour le score deepfake, modèle d'estimation
d'âge pour le pré-check mineur, pHash. Ici : mocks (cacher la réponse CV pour la démo, R-06).
"""

from __future__ import annotations

import hashlib

from .config import DEEPFAKE_SCORE_THRESHOLD
from .types import ForensicRecord, MediaItem, Status, utcnow


async def _suspected_minor(item: MediaItem) -> bool:
    """MOCK. Le vrai : estimation d'âge AVANT tout stockage (G-6).

    En démo, on déclenche par un flag dans l'URL, JAMAIS par une image de mineur
    (voir premortem E2 : le système ne télécharge même pas).
    """
    return "minor" in item.url


async def _cv_score(item: MediaItem) -> float:
    """MOCK Sightengine. Le vrai : détecteur de média synthétique 0.0-1.0."""
    return 0.94


async def analyze(item: MediaItem, *, log=print) -> ForensicRecord:
    """Consomme un MediaItem in-scope, renvoie un ForensicRecord."""
    # G-6 : le pré-check mineur tourne AVANT tout stockage. Non négociable (spec §12).
    if await _suspected_minor(item):
        log("[ANALYZE] mineur suspecté -> ESCALATE : aucun download, aucun hash, aucun stockage")
        return _record(item, score=0.0, phash="", sha="", status=Status.ESCALATED)

    score = await _cv_score(item)
    if score < DEEPFAKE_SCORE_THRESHOLD:
        log(f"[ANALYZE] score {score:.2f} < {DEEPFAKE_SCORE_THRESHOLD} -> REJECTED, aucun octet stocké")
        return _record(item, score=score, phash="", sha="", status=Status.REJECTED)

    # G-5 : hash perceptuel préféré aux octets bruts.
    phash = f"phash:{hashlib.sha1(item.url.encode()).hexdigest()[:16]}"       # MOCK pHash
    sha = hashlib.sha256(item.url.encode()).hexdigest()                        # MOCK (vrai : hash de la capture)
    log(f"[ANALYZE] score {score:.2f} >= seuil -> VERIFIED, preuve minimale (phash + sha256)")
    return _record(item, score=score, phash=phash, sha=sha, status=Status.VERIFIED)


def _record(item: MediaItem, *, score: float, phash: str, sha: str, status: Status) -> ForensicRecord:
    return ForensicRecord(
        case_id=item.case_id,
        source_url=item.url,
        deepfake_score=score,
        perceptual_hash=phash,
        sha256_hash=sha,
        discovery_ts_utc=utcnow(),
        status=status,
    )
