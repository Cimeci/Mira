"""Stage 2 — L'Analyzer. Pré-check mineur, vérification forensique, preuve minimale.

Lane L2. Le vrai : API CV (Sightengine) pour le score deepfake, pHash. Ici : mocks
(cacher la réponse CV pour la démo, R-06).

Verrou d'ordre G-6 — structurel, pas conventionnel
--------------------------------------------------
`analyze()` est découpé en 4 phases nommées qui s'exécutent dans cet ordre :

  1. `_phase_precheck_minor`   — signaux NON-binaires uniquement (tokens URL/metadata).
  2. `_phase_face_match`       — le média correspond-il au visage du mandat ?
                                 (services/face-verifier ; la décision isMatch
                                 appartient au service — mock ici).
  3. `_phase_score`            — score deepfake, toujours sans toucher aux octets.
  4. `_phase_capture_and_hash` — le SEUL endroit du système autorisé à toucher des
                                 octets média, via le hook `_fetch_bytes`.

La phase 4 est INATTEIGNABLE si la phase 1 escalade ou si la phase 2 ou 3 rejette :
`analyze()` fait un early return structurel — pas de flag, pas de branche à oublier.
Un refactor qui déplacerait le download avant le pré-check devrait réécrire les
4 phases ET casser tests/test_analyzer_order.py + tests/test_face_match.py.
Le face-match tourne APRÈS le pré-check mineur, jamais avant : analyser le visage
d'un mineur suspecté est déjà le mal qu'on évite (même logique que
PIXEL_AGE_ESTIMATION_FORBIDDEN).

PIXEL_AGE_ESTIMATION_FORBIDDEN : l'estimation d'âge sur pixels est INTERDITE ici,
y compris « pour améliorer le pré-check ». Analyser l'image d'un mineur EST déjà
le mal qu'on évite (G-6) — le pré-check ne consomme donc QUE des signaux
non-binaires : tokens d'URL, nom de fichier, contexte de la page.
"""

from __future__ import annotations

import hashlib
import logging

from .config import DEEPFAKE_SCORE_THRESHOLD
from .events import Emit, make_event, print_emitter
from .types import ForensicRecord, MediaItem, Status, utcnow

# Même canal de trace dev que l'orchestrateur : silencieux en démo, stacktrace
# complète avec logging.basicConfig(level=logging.DEBUG).
_logger = logging.getLogger("mira")

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
    """MOCK Sightengine. Le vrai : détecteur de média synthétique 0.0-1.0 (sur l'URL,
    pas sur des octets stockés par nous)."""
    return 0.94


async def _face_match(item: MediaItem) -> tuple[bool, float | None]:
    """MOCK face-verifier. Le vrai : POST services/face-verifier /api/verify avec
    l'embedding de référence du case (enrôlé via /api/enroll).

    La décision is_match appartient au SERVICE (seuil sur la distance euclidienne,
    MATCH_DISTANCE_THRESHOLD côté TS) — le score renvoyé (similarityScore, ou None
    si aucun visage détecté) n'est qu'indicatif, jamais re-seuillé ici.
    """
    return True, 0.91


def _fetch_bytes(item: MediaItem) -> bytes:
    """Hook unique d'accès aux octets média. MOCK : encode l'URL, zéro réseau.

    Appelé UNIQUEMENT par `_phase_capture_and_hash` — si ce hook tourne sur un cas
    escaladé ou rejeté, c'est un bug G-6 (tests/test_analyzer_order.py le prouve
    en le remplaçant par une bombe RuntimeError).
    """
    return item.url.encode()


async def _phase_precheck_minor(item: MediaItem) -> str | None:
    """Phase 1/4 — pré-check mineur AVANT tout octet (G-6). Token détecté ou None."""
    return await _suspected_minor(item)


async def _phase_face_match(item: MediaItem) -> tuple[bool, float | None]:
    """Phase 2/4 — le média montre-t-il le visage de la victime du mandat ?

    Tourne APRÈS le pré-check mineur (G-6), jamais avant. Aucun octet touché tant
    que le hook est un mock ; au branchement réel, l'équipe tranche si les octets
    passent par `_fetch_bytes` ou si le service fetch l'URL lui-même — dans les
    deux cas post-pré-check.
    """
    return await _face_match(item)


async def _phase_score(item: MediaItem) -> float:
    """Phase 3/4 — score deepfake. Toujours aucun octet touché ni stocké."""
    return await _cv_score(item)


async def _phase_capture_and_hash(item: MediaItem) -> tuple[str, str]:
    """Phase 4/4 — LE seul endroit qui touche des octets média (via `_fetch_bytes`).

    G-5 : on ne retient que des empreintes (phash + sha256), jamais les octets bruts.
    """
    data = _fetch_bytes(item)
    phash = f"phash:{hashlib.sha1(data).hexdigest()[:16]}"  # MOCK pHash
    sha = hashlib.sha256(data).hexdigest()  # MOCK (vrai : hash de la capture)
    return phash, sha


async def analyze(item: MediaItem, *, log=print, emit: Emit = print_emitter) -> ForensicRecord:
    """Consomme un MediaItem in-scope, renvoie un ForensicRecord. Émet la transition d'état.

    Ordre G-6 verrouillé par la structure : precheck -> face-match -> score -> capture,
    avec early return à chaque garde — `_phase_capture_and_hash` est inatteignable si
    escalade, visage sans correspondance, ou score sous le seuil.
    """
    # Phase 1 — G-6 : le pré-check mineur tourne AVANT tout stockage. Non négociable (§12).
    try:
        token = await _phase_precheck_minor(item)
    except Exception as exc:
        # Précaution G-6 : un pré-check EN PANNE ne peut pas exclure un mineur -> le cas
        # est traité comme une suspicion (halt + escalade), JAMAIS comme un FAILED
        # générique indiscernable d'un timeout CV. Ici, même les erreurs de contrat
        # n'ont pas le droit de contourner l'escalade — c'est l'exception délibérée à
        # la politique _CONTRACT_ERRORS de l'orchestrateur. Le message d'exception ne
        # sort jamais (URL/PII possible) : type seulement, stacktrace sur le logger dev.
        _logger.debug("pré-check mineur en panne sur %s", item.case_id, exc_info=exc)
        log(
            f"[ANALYZE] pré-check G-6 en panne ({type(exc).__name__}) "
            "-> escalade par précaution"
        )
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.ESCALATED,
            from_status=Status.LOCATED,
            detail=(
                f"[ANALYZE] pré-check mineur en panne ({type(exc).__name__}) -> ESCALATE "
                "par précaution : aucun download, aucun hash, aucun stockage"
            ),
            payload={"reason": "precheck_failure"},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.ESCALATED)
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

    # Phase 2 — face match : n'avancer que si le média correspond au visage du mandat.
    # Un non-match n'est PAS un deepfake de la victime -> hors mandat, REJECTED.
    is_match, face_score = await _phase_face_match(item)
    if not is_match:
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.REJECTED,
            from_status=Status.LOCATED,
            detail=(
                "[ANALYZE] face-match négatif : le média ne correspond pas au visage "
                "du mandat -> REJECTED, aucun octet stocké"
            ),
            payload={"url": item.url, "reason": "face_mismatch", "face_score": face_score},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.REJECTED)
    face_score_txt = "n/a" if face_score is None else f"{face_score:.2f}"
    log(f"[ANALYZE] face-match : visage du mandat confirmé (score {face_score_txt})")

    # Phase 3 — score, toujours sans octets.
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

    # Phase 4 — atteinte UNIQUEMENT si ni escalade ni rejet. G-5 : empreintes seulement.
    phash, sha = await _phase_capture_and_hash(item)
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
    return _record(item, score=score, phash=phash, sha=sha, status=Status.VERIFIED)


def _record(
    item: MediaItem, *, score: float, phash: str, sha: str, status: Status
) -> ForensicRecord:
    return ForensicRecord(
        case_id=item.case_id,
        source_url=item.url,
        deepfake_score=score,
        perceptual_hash=phash,
        sha256_hash=sha,
        discovery_ts_utc=utcnow(),
        status=status,
    )
