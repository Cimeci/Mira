"""Real ArcFace recognition (mira/face). The match math runs always; the real
insightface recognition runs only when insightface is installed AND the three fixture
photos exist (see tests/fixtures/faces/README.md) — i.e. locally with the model, or
on the GPU VM. Distinct from tests/test_face_match.py (the analyzer phase-order test).
"""

from __future__ import annotations

from importlib.util import find_spec
from pathlib import Path

import pytest

from mira.face import EMBEDDING_LENGTH, cosine_distance, is_match, match_distance

_FIXTURES = Path(__file__).parent / "fixtures" / "faces"
_PHOTOS = ("reference.jpg", "same_person.jpg", "other_person.jpg")


def test_match_logic():
    a = [1.0] + [0.0] * (EMBEDDING_LENGTH - 1)
    b = [0.0, 1.0] + [0.0] * (EMBEDDING_LENGTH - 2)
    assert is_match(cosine_distance(a, a)) is True  # identical → match
    assert is_match(cosine_distance(a, b)) is False  # orthogonal → no match
    # match-any-face: victim present among several faces → match; absent → not
    assert is_match(match_distance(a, [b, a])) is True
    assert is_match(match_distance(a, [b, b])) is False
    assert match_distance(a, []) == 1.0  # no face detected → no match


_ready = find_spec("insightface") is not None and all(
    (_FIXTURES / name).exists() for name in _PHOTOS
)


@pytest.mark.skipif(
    not _ready,
    reason="needs insightface + tests/fixtures/faces/{reference,same_person,other_person}.jpg",
)
def test_real_face_recognition():
    from mira import face

    ref = face.embed((_FIXTURES / "reference.jpg").read_bytes())  # enrollment: largest face
    same = face.embed_all((_FIXTURES / "same_person.jpg").read_bytes())  # match: every face
    other = face.embed_all((_FIXTURES / "other_person.jpg").read_bytes())

    d_same = match_distance(ref, same)
    d_other = match_distance(ref, other)

    assert is_match(d_same), f"victim should match (best dist={d_same:.3f})"
    assert not is_match(d_other), f"stranger should not match (best dist={d_other:.3f})"
    assert d_same < d_other, f"victim must be closer than a stranger ({d_same:.3f} vs {d_other:.3f})"  # noqa: E501
