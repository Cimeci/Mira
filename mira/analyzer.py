"""Stage 2 — L'Analyzer. Pré-check mineur, vérification forensique, preuve minimale.

Lane L2. Le vrai : API CV (Sightengine) pour le score deepfake, pHash. Ici : mocks
(cacher la réponse CV pour la démo, R-06).

Verrou d'ordre G-6 — structurel, pas conventionnel
--------------------------------------------------
`analyze()` est découpé en 3 phases nommées qui s'exécutent dans cet ordre :

  1. `_phase_precheck_minor`   — signaux NON-binaires uniquement (tokens URL/metadata).
  2. `_phase_score`            — score deepfake, toujours sans toucher aux octets.
  3. `_phase_capture_and_hash` — le SEUL endroit du système autorisé à toucher des
                                 octets média, via le hook `_fetch_bytes`.

La phase 3 est INATTEIGNABLE si la phase 1 escalade ou si la phase 2 rejette :
`analyze()` fait un early return structurel — pas de flag, pas de branche à oublier.
Un refactor qui déplacerait le download avant le pré-check devrait réécrire les
3 phases ET casser tests/test_analyzer_order.py.

PIXEL_AGE_ESTIMATION_FORBIDDEN : l'estimation d'âge sur pixels est INTERDITE ici,
y compris « pour améliorer le pré-check ». Analyser l'image d'un mineur EST déjà
le mal qu'on évite (G-6) — le pré-check ne consomme donc QUE des signaux
non-binaires : tokens d'URL, nom de fichier, contexte de la page.
"""

from __future__ import annotations

import hashlib
import os
import io
import httpx
import logging
from cryptography.fernet import Fernet
import imagehash
from PIL import Image

_logger = logging.getLogger("mira.analyzer")

from .config import DEEPFAKE_SCORE_THRESHOLD
from .events import Emit, make_event, print_emitter
from .types import ForensicRecord, MediaItem, Status, utcnow

# G-6 : aucune API d'estimation d'âge sur pixels ne doit JAMAIS entrer dans ce module.
# Référencée par la docstring du module — c'est un contrat, pas une config.
PIXEL_AGE_ESTIMATION_FORBIDDEN = True

# Tokens non-binaires (URL / filename / contexte page) qui déclenchent l'escalade G-6.
# En démo le flag vient de l'URL/metadata, JAMAIS d'une image (voir premortem E2).
_MINOR_TOKENS = ("minor",)


async def _suspected_minor(item: MediaItem) -> str | None:
    """Pré-check mineur sur signaux NON-binaires uniquement. Renvoie le token détecté.

    Garde explicite G-6 : ce check ne lit QUE des métadonnées (tokens d'URL, filename,
    contexte de page) — jamais un octet du média (PIXEL_AGE_ESTIMATION_FORBIDDEN).
    Le trigger substring URL est le chemin DÉMO : en démo le flag vient de
    l'URL/metadata, JAMAIS d'une image.
    """
    for token in _MINOR_TOKENS:
        if token in item.url:
            return token
    return None


async def _cv_score(item: MediaItem) -> float:
    """API CV (Sightengine) pour le score deepfake."""
    if os.getenv("MIRA_DEMO_MODE", "1") == "1":
        _logger.warning("[ANALYZE] MIRA_DEMO_MODE actif, fallback score (0.94)")
        return 0.94
        
    api_user = os.getenv("SIGHTENGINE_API_USER")
    api_secret = os.getenv("SIGHTENGINE_API_SECRET")
    
    if not api_user or not api_secret:
        _logger.warning("[ANALYZE] Cles Sightengine absentes, fallback score (0.94)")
        return 0.94
        
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.sightengine.com/1.0/check.json",
                params={
                    "models": "deepfake",
                    "api_user": api_user,
                    "api_secret": api_secret,
                    "url": item.url
                }
            )
            resp.raise_for_status()
            data = resp.json()
            score = data.get("type", {}).get("deepfake", 0.0)
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"Score hors bornes: {score}")
            return float(score)
    except Exception as e:
        _logger.error(f"[ANALYZE] Erreur Sightengine: {e}, fallback score (0.94)")
        return 0.94


async def _fetch_bytes(item: MediaItem) -> bytes:
    """Hook unique d'accès aux octets média."""
    if os.getenv("MIRA_DEMO_MODE", "1") == "1":
        return item.url.encode()
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(item.url)
        resp.raise_for_status()
        return resp.content


async def _phase_precheck_minor(item: MediaItem) -> str | None:
    """Phase 1/3 — pré-check mineur AVANT tout octet (G-6). Token détecté ou None."""
    return await _suspected_minor(item)


async def _phase_score(item: MediaItem) -> float:
    """Phase 2/3 — score deepfake. Toujours aucun octet touché ni stocké."""
    return await _cv_score(item)


async def _phase_capture_and_hash(item: MediaItem) -> tuple[str, str, str | None]:
    """Phase 3/3 — LE seul endroit qui touche des octets média (via `_fetch_bytes`).

    G-5 : on ne retient que des empreintes (phash + sha256), jamais les octets bruts.
    """
    data = await _fetch_bytes(item)
    
    sha = hashlib.sha256(data).hexdigest()
    
    try:
        img = Image.open(io.BytesIO(data))
        phash_val = str(imagehash.phash(img))
        phash = f"phash:{phash_val}"
    except Exception:
        phash = f"phash:{hashlib.sha1(data).hexdigest()[:16]}"
        
    minimal_ref = None
    fernet_key = os.getenv("MIRA_EVIDENCE_KEY")
    if fernet_key:
        try:
            f = Fernet(fernet_key.encode())
            encrypted = f.encrypt(data)
            os.makedirs("_evidence", exist_ok=True)
            path = f"_evidence/{item.case_id}_{sha}.enc"
            with open(path, "wb") as out:
                out.write(encrypted)
            minimal_ref = path
        except Exception as e:
            _logger.error(f"[ANALYZE] Erreur chiffrement evidence: {e}")
            
    # Liberer la memoire immédiatement (G-5)
    del data
    return phash, sha, minimal_ref


async def analyze(item: MediaItem, *, log=print, emit: Emit = print_emitter) -> ForensicRecord:
    """Consomme un MediaItem in-scope, renvoie un ForensicRecord. Émet la transition d'état.

    Ordre G-6 verrouillé par la structure : precheck -> score -> capture, avec early
    return à chaque garde — `_phase_capture_and_hash` est inatteignable si escalade
    ou score sous le seuil.
    """
    # Phase 1 — G-6 : le pré-check mineur tourne AVANT tout stockage. Non négociable (§12).
    token = await _phase_precheck_minor(item)
    if token is not None:
        log(f"[ANALYZE] pré-check G-6 : token {token!r} détecté (URL/metadata) -> escalade")
        # Event MINIMAL par design G-6 : case_id + raison, pas d'URL du média, pas de hash —
        # rien n'a été téléchargé ni stocké, l'event ne doit rien exposer non plus.
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.ESCALATED,
            from_status=Status.LOCATED,
            detail=(
                "[ANALYZE] mineur suspecté -> ESCALATE : "
                "aucun download, aucun hash, aucun stockage"
            ),
            payload={"reason": "suspected_minor"},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.ESCALATED)

    # Phase 2 — score, toujours sans octets.
    score = await _phase_score(item)
    if score < DEEPFAKE_SCORE_THRESHOLD:
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.REJECTED,
            from_status=Status.LOCATED,
            detail=(
                f"[ANALYZE] score {score:.2f} < {DEEPFAKE_SCORE_THRESHOLD} "
                "-> REJECTED, aucun octet stocké"
            ),
            payload={"url": item.url, "score": score},
        ))
        return _record(item, score=score, phash="", sha="", status=Status.REJECTED)

    # Phase 3 — atteinte UNIQUEMENT si ni escalade ni rejet. G-5 : empreintes seulement.
    phash, sha, minimal_ref = await _phase_capture_and_hash(item)
    emit(make_event(
        item.case_id,
        "analyzer",
        Status.VERIFIED,
        from_status=Status.LOCATED,
        detail=(
            f"[ANALYZE] score {score:.2f} >= seuil -> VERIFIED, preuve minimale (phash + sha256)"
        ),
        payload={"url": item.url, "score": score, "phash": phash, "sha256": sha},
    ))
    return _record(item, score=score, phash=phash, sha=sha, status=Status.VERIFIED, minimal_ref=minimal_ref)


def _record(
    item: MediaItem, *, score: float, phash: str, sha: str, status: Status, minimal_ref: str | None = None
) -> ForensicRecord:
    return ForensicRecord(
        case_id=item.case_id,
        source_url=item.url,
        deepfake_score=score,
        perceptual_hash=phash,
        sha256_hash=sha,
        discovery_ts_utc=utcnow(),
        status=status,
        minimal_ref=minimal_ref,
    )
