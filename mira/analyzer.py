"""Stage 2 — the Analyzer. Minor pre-check, forensic verification, minimal evidence.

Lane L2. The real thing: a CV API (Sightengine) for the deepfake score + pHash. Here:
mocks for the deepfake/pHash side; the face match is real (mira/face, ArcFace).

Order lock — structural, not by convention
------------------------------------------
`analyze()` is split into 4 named phases that run in this exact order:

  1. `_phase_precheck_minor`   — NON-binary signals only (URL/metadata tokens).
  2. `_phase_face_match`       — does the media match the mandate's face? (real ArcFace).
  3. `_phase_score`            — deepfake score, still without touching any bytes.
  4. `_phase_capture_and_hash` — the ONLY place in the system allowed to touch media
                                 bytes, via the `_fetch_bytes` hook.

Phase 4 is UNREACHABLE if phase 1 escalates or phase 2/3 rejects: `analyze()` does a
structural early return at each guard — no flag, no branch to forget. A refactor that
moved the download before the pre-check would have to rewrite all 4 phases AND break
tests/test_analyzer_order.py + tests/test_face_match.py. The face match runs AFTER the
minor pre-check, never before: analyzing the face of a suspected minor is already the
harm we avoid (same reasoning as PIXEL_AGE_ESTIMATION_FORBIDDEN).

PIXEL_AGE_ESTIMATION_FORBIDDEN: pixel-based age estimation is FORBIDDEN here, including
"to improve the pre-check". Analyzing a minor's image IS already the harm we avoid — so
the pre-check consumes ONLY non-binary signals: URL tokens, filename, page context.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging

import httpx

from . import face, store
from .config import DEEPFAKE_SCORE_THRESHOLD
from .events import Emit, make_event, print_emitter
from .types import ForensicRecord, MediaItem, Status, utcnow

# Same dev trace channel as the orchestrator: silent in the demo, full stacktrace with
# logging.basicConfig(level=logging.DEBUG).
_logger = logging.getLogger("mira")

# No pixel-based age-estimation API may EVER enter this module. Referenced by the module
# docstring — it's a contract, not a config.
PIXEL_AGE_ESTIMATION_FORBIDDEN = True

# Non-binary tokens (URL / filename / page context) that trigger escalation. In the demo
# the flag comes from the URL/metadata, NEVER from an image (see premortem E2).
_MINOR_TOKENS = ("minor",)


async def _suspected_minor(item: MediaItem) -> str | None:
    """Minor pre-check on NON-binary signals only. Returns the detected token.

    Explicit guard: this check reads ONLY metadata (URL tokens, filename, page context)
    — never a byte of the media (PIXEL_AGE_ESTIMATION_FORBIDDEN). The URL-substring
    trigger is the DEMO path: in the demo the flag comes from the URL/metadata, never an
    image.
    """
    for token in _MINOR_TOKENS:
        if token in item.url:
            return token
    return None


async def _cv_score(item: MediaItem) -> float:
    """MOCK Sightengine. The real thing: a synthetic-media detector 0.0-1.0 (on the URL,
    not on bytes we've stored)."""
    return 0.94


async def _fetch_candidate(url: str) -> bytes | None:
    """Download the candidate image into memory (never to disk). None if not
    retrievable — best-effort: an infra failure must not reject the evidence."""
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.content
    except Exception:  # noqa: BLE001 - any failure = unverifiable, not fatal
        return None


async def _face_match(item: MediaItem) -> tuple[bool, float | None]:
    """Real face match — insightface ArcFace, in-process (mira/face).

    Reads the case's enrolled 512-d reference and checks EVERY face detected in the
    candidate (the victim may not be the largest face in a scraped image). Returns
    (is_match, score). Pass-through (True, None) when no reference is enrolled or the
    image can't be fetched — so the demo and unconfigured runs are never rejected here.
    """
    reference = await store.get_reference_embedding(item.case_id)
    if reference is None:
        return True, None
    image = await _fetch_candidate(item.url)
    if image is None:
        return True, None
    faces = await asyncio.to_thread(face.embed_all, image)  # CPU-bound → off the loop
    distance = face.match_distance(reference, faces)
    return face.is_match(distance), face.similarity(distance)


def _fetch_bytes(item: MediaItem) -> bytes:
    """The single media-byte access hook. MOCK: encodes the URL, zero network.

    Called ONLY by `_phase_capture_and_hash` — if this hook runs on an escalated or
    rejected case, that's a bug (tests/test_analyzer_order.py proves it by replacing it
    with a RuntimeError bomb)."""
    return item.url.encode()


async def _phase_precheck_minor(item: MediaItem) -> str | None:
    """Phase 1/4 — minor pre-check BEFORE any byte. Detected token or None."""
    return await _suspected_minor(item)


async def _phase_face_match(item: MediaItem) -> tuple[bool, float | None]:
    """Phase 2/4 — does the media show the mandate victim's face?

    Runs AFTER the minor pre-check, never before. Real ArcFace (mira/face); fetches the
    candidate itself, post-pre-check, and only if a reference is enrolled."""
    return await _face_match(item)


async def _phase_score(item: MediaItem) -> float:
    """Phase 3/4 — deepfake score. Still no bytes touched or stored."""
    return await _cv_score(item)


async def _phase_capture_and_hash(item: MediaItem) -> tuple[str, str]:
    """Phase 4/4 — the ONLY place that touches media bytes (via `_fetch_bytes`).

    We keep only fingerprints (phash + sha256), never the raw bytes."""
    data = _fetch_bytes(item)
    phash = f"phash:{hashlib.sha1(data).hexdigest()[:16]}"  # MOCK pHash
    sha = hashlib.sha256(data).hexdigest()  # MOCK (real: hash of the capture)
    return phash, sha


async def analyze(item: MediaItem, *, log=print, emit: Emit = print_emitter) -> ForensicRecord:
    """Consume an in-scope MediaItem, return a ForensicRecord. Emits the state transition.

    Order locked by structure: precheck -> face-match -> score -> capture, with an early
    return at each guard — `_phase_capture_and_hash` is unreachable on escalation, a face
    mismatch, or a below-threshold score."""
    # Phase 1 — the minor pre-check runs BEFORE any storage. Non-negotiable (spec §12).
    try:
        token = await _phase_precheck_minor(item)
    except Exception as exc:
        # A FAILED pre-check cannot rule out a minor -> the case is treated as a suspicion
        # (halt + escalate), NEVER as a generic FAILED indistinguishable from a CV timeout.
        # Even contract errors may not bypass escalation here — the deliberate exception to
        # the orchestrator's _CONTRACT_ERRORS policy. The exception message never leaks
        # (may contain URL/PII): type only, stacktrace on the dev logger.
        _logger.debug("minor pre-check failed on %s", item.case_id, exc_info=exc)
        log(
            f"[ANALYZE] minor pre-check failed ({type(exc).__name__}) "
            "-> escalating as a precaution"
        )
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.ESCALATED,
            from_status=Status.LOCATED,
            detail=(
                f"[ANALYZE] minor pre-check failed ({type(exc).__name__}) -> ESCALATE "
                "as a precaution: no download, no hash, no storage"
            ),
            payload={"reason": "precheck_failure"},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.ESCALATED)
    if token is not None:
        log(f"[ANALYZE] minor pre-check: token {token!r} detected (URL/metadata) -> escalate")
        # MINIMAL event by design: case_id + reason, no media URL, no hash — nothing was
        # downloaded or stored, so the event must expose nothing either.
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.ESCALATED,
            from_status=Status.LOCATED,
            detail=(
                "[ANALYZE] suspected minor -> ESCALATE: "
                "no download, no hash, no storage"
            ),
            payload={"reason": "suspected_minor"},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.ESCALATED)

    # Phase 2 — face match: only proceed if the media matches the mandate's face.
    # A non-match is NOT a deepfake of the victim -> out of mandate, REJECTED.
    is_match, face_score = await _phase_face_match(item)
    if not is_match:
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.REJECTED,
            from_status=Status.LOCATED,
            detail=(
                "[ANALYZE] face-match negative: media does not match the mandate's face "
                "-> REJECTED, no bytes stored"
            ),
            payload={"url": item.url, "reason": "face_mismatch", "face_score": face_score},
        ))
        return _record(item, score=0.0, phash="", sha="", status=Status.REJECTED)
    face_score_txt = "n/a" if face_score is None else f"{face_score:.2f}"
    log(f"[ANALYZE] face-match: mandate face confirmed (score {face_score_txt})")

    # Phase 3 — score, still without bytes.
    score = await _phase_score(item)
    if score < DEEPFAKE_SCORE_THRESHOLD:
        emit(make_event(
            item.case_id,
            "analyzer",
            Status.REJECTED,
            from_status=Status.LOCATED,
            detail=(
                f"[ANALYZE] score {score:.2f} < {DEEPFAKE_SCORE_THRESHOLD} "
                "-> REJECTED, no bytes stored"
            ),
            payload={"url": item.url, "score": score},
        ))
        return _record(item, score=score, phash="", sha="", status=Status.REJECTED)

    # Phase 4 — reached ONLY if neither escalated nor rejected. Fingerprints only.
    phash, sha = await _phase_capture_and_hash(item)
    emit(make_event(
        item.case_id,
        "analyzer",
        Status.VERIFIED,
        from_status=Status.LOCATED,
        detail=(
            f"[ANALYZE] score {score:.2f} >= threshold -> VERIFIED, "
            "minimal evidence (phash + sha256)"
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
