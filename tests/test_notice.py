"""Snapshot du verrou légal G-9 : citations exactes, jamais de pénalité inventée."""

import pytest

from mira.notifier import _draft_dsa_notice, _resolve_host, assert_no_invented_penalty
from mira.types import ForensicRecord, Mandate, Status, utcnow

_REQUIRED_REFERENCES = [
    "Code pénal art. 226-8-1",
    "loi SREN n° 2024-449",
    "DSA art. 16",
    "LCEN",
]


def _mandate(role: str = "victim") -> Mandate:
    # Mandate construit directement (pas via capture_consent) : pas d'artefact écrit en test.
    return Mandate(
        case_id="t-notice",
        requester_role=role,
        consent_ts_utc=utcnow(),
        scope_urls=["https://mock-host.local/target"],
    )


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
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate())
    for ref in _REQUIRED_REFERENCES:
        assert ref in notice, f"référence légale manquante : {ref}"


def test_notice_contains_good_faith_declaration():
    # DSA art. 16(2)(d) : la déclaration de bonne foi est une exigence de validité de la notice.
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate())
    assert "Déclaration de bonne foi" in notice
    assert "16(2)(d)" in notice


def test_notice_identifies_notifier_with_email():
    # DSA art. 16(2)(c) : nom + email du notifiant obligatoires (l'anonymat ne couvre
    # que le CSAM) — sans eux, pas de « connaissance effective » art. 16(3).
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate())
    assert "16(2)(c)" in notice
    assert "@" in notice.split("adresse électronique :")[1].splitlines()[0]


def test_ai_transparency_is_voluntary_not_normative():
    # L'AI Act art. 50 n'impose rien ici : afficher une obligation inexistante serait
    # relevé par un juriste au jury — la transparence est présentée comme volontaire.
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate())
    assert "démarche volontaire" in notice
    assert "(AI Act) :" not in notice


def test_notice_never_mentions_penalty():
    # G-9 : une pénalité (même exacte) n'a rien à faire dans la notice ; inventée = disqualifiant.
    notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate())
    assert assert_no_invented_penalty(notice) == notice


def test_notifier_line_follows_requester_role():
    # La ligne « Notifiant » décrit le mandat reçu, sans inventer de base légale (G-9).
    for role, fragment in [
        ("victim", "de la personne concernée"),
        ("legal_rep", "de son représentant légal mandaté"),
        ("authorized_ngo", "d'une ONG autorisée"),
    ]:
        notice = _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate(role))
        assert fragment in notice


def test_unknown_role_fails_fast():
    with pytest.raises(KeyError):
        _draft_dsa_notice(_verified_record(), _resolve_host("x"), _mandate("stalker"))


def test_penalty_guard_blocks_llm_output():
    for bad in [
        "encourt une amende de 45 000 euros",
        "passible de 2 ans d'emprisonnement",
        "sous peine de sanction",
        "45 000 €",
        "1 euro symbolique",
        "risque une condamnation",
        "pénalité applicable",
        "réclusion criminelle",
    ]:
        with pytest.raises(ValueError):
            assert_no_invented_penalty(bad)


def test_penalty_guard_allows_legitimate_legal_language():
    # Les frontières de mot évitent les faux positifs sur le vocabulaire UE légitime.
    for ok in [
        "conformément au droit européen",
        "le règlement européen 2022/2065",
        "l'Union européenne",
    ]:
        assert assert_no_invented_penalty(ok) == ok
