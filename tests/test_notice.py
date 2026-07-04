"""Snapshot du verrou légal G-9 : citations exactes, jamais de pénalité inventée."""

import pytest

from mira.notifier import _draft_dsa_notice, _resolve_host, assert_no_invented_penalty
from mira.types import ForensicRecord, Status, utcnow

_REQUIRED_REFERENCES = [
    "Code pénal art. 226-8-1",
    "loi SREN n° 2024-449",
    "DSA art. 16",
    "LCEN",
]


def _verified_record() -> ForensicRecord:
    return ForensicRecord(
        case_id="t-notice",
        source_url="https://mock-host.local/target/synthetic_test.jpg",
        deepfake_score=0.94,
        perceptual_hash="phash:abc123",
        sha256_hash="deadbeef",
        discovery_ts_utc=utcnow(),
        status=Status.VERIFIED,
    )


def test_notice_cites_exact_legal_references():
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"))
    for ref in _REQUIRED_REFERENCES:
        assert ref in notice, f"référence légale manquante : {ref}"


def test_notice_contains_good_faith_declaration():
    # G-8 / LCEN : la déclaration de bonne foi est une exigence de validité de la notice.
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"))
    assert "Déclaration de bonne foi" in notice
    assert "bonne foi" in notice


def test_notice_never_mentions_penalty():
    # G-9 : une pénalité (même exacte) n'a rien à faire dans la notice ; inventée = disqualifiant.
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"))
    assert assert_no_invented_penalty(notice) == notice


def test_penalty_guard_blocks_llm_output():
    for bad in [
        "encourt une amende de 45 000 euros",
        "passible de 2 ans d'emprisonnement",
        "sous peine de sanction",
        "45 000 €",
    ]:
        with pytest.raises(ValueError):
            assert_no_invented_penalty(bad)
