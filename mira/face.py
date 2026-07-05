"""Real face recognition — insightface (SCRFD detect + ArcFace 512-d embed).

Heavy deps (insightface, onnxruntime, cv2) are imported lazily, so importing this
module costs nothing until an embedding is computed — the mock/demo path never pays
for it. Enrollment uses the largest face (the victim poses solo for her signature);
matching checks EVERY detected face, since the victim may not be the largest (or only)
face in a scraped image.
"""

from __future__ import annotations

import math
import os
from collections.abc import Iterable

EMBEDDING_LENGTH = 512

# Below this cosine distance, two ArcFace vectors are the same person. Tunable via
# MIRA_MATCH_THRESHOLD; 0.6 (cosine sim > 0.4) is a safe default for buffalo_l.
MATCH_COSINE_DISTANCE_THRESHOLD = float(os.getenv("MIRA_MATCH_THRESHOLD", "0.6"))


class NoFaceDetectedError(RuntimeError):
    """No detectable face — never return a zero vector (a false match against anything)."""


def cosine_distance(a: Iterable[float], b: Iterable[float]) -> float:
    """1 - cosine similarity. 0 = identical direction (ArcFace convention)."""
    a, b = list(a), list(b)
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 1.0
    return 1.0 - dot / (na * nb)


def is_match(distance: float) -> bool:
    return distance < MATCH_COSINE_DISTANCE_THRESHOLD


def match_distance(reference: Iterable[float], candidate_faces: list[list[float]]) -> float:
    """Smallest cosine distance from ANY detected face to the reference. 1.0 (no match)
    when the image had no detectable face — the victim may not be the largest face."""
    reference = list(reference)
    if not candidate_faces:
        return 1.0
    return min(cosine_distance(reference, face) for face in candidate_faces)


def similarity(distance: float) -> float:
    """Display score in [0, 1] from a cosine distance (higher = more similar)."""
    return max(0.0, 1.0 - distance)


_app = None


def _get_app():
    global _app
    if _app is None:
        try:
            from insightface.app import FaceAnalysis
        except ImportError as e:
            raise RuntimeError(
                "insightface not installed — pip install insightface onnxruntime "
                "opencv-python-headless"
            ) from e
        _app = FaceAnalysis(name="buffalo_l")
        _app.prepare(ctx_id=int(os.getenv("MIRA_FACE_CTX_ID", "0")))  # 0 = GPU, -1 = CPU
    return _app


def _decode(image: bytes):
    import cv2
    import numpy as np

    arr = cv2.imdecode(np.frombuffer(image, np.uint8), cv2.IMREAD_COLOR)
    if arr is None:
        raise ValueError("undecodable image bytes")
    return arr


def embed(image: bytes) -> list[float]:
    """Largest face only — for ENROLLMENT (victim's solo signature photo)."""
    faces = _get_app().get(_decode(image))
    if not faces:
        raise NoFaceDetectedError()
    largest = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    vector = largest.normed_embedding.tolist()
    assert len(vector) == EMBEDDING_LENGTH  # ArcFace contract
    return vector


def embed_all(image: bytes) -> list[list[float]]:
    """Every detected face — for MATCHING. Empty list if no face is found."""
    return [f.normed_embedding.tolist() for f in _get_app().get(_decode(image))]


def crop_faces(image: bytes, *, margin: float = 0.15) -> list[bytes]:
    """Face-only JPEG crop of each detected face — no body. Crop before sending to an
    external LLM so only the face, never a nude body, ever leaves the system."""
    import cv2

    arr = _decode(image)
    height, width = arr.shape[:2]
    crops: list[bytes] = []
    for face in _get_app().get(arr):
        x1, y1, x2, y2 = face.bbox
        pad_w, pad_h = margin * (x2 - x1), margin * (y2 - y1)
        x1, y1 = max(0, int(x1 - pad_w)), max(0, int(y1 - pad_h))
        x2, y2 = min(width, int(x2 + pad_w)), min(height, int(y2 + pad_h))
        ok, buf = cv2.imencode(".jpg", arr[y1:y2, x1:x2])
        if ok:
            crops.append(buf.tobytes())
    return crops
