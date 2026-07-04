"""Tests de capture_consent : le mandat ne peut pas exister sans consentement valide."""

import base64
import json

import pytest

from mira.mandate import capture_consent, verify_consent_artifact
from mira.orchestrator import ConsentError


def _capture(**overrides):
    kwargs = dict(
        case_id="t-001",
        requester_role="victim",
        scope_urls=["https://mock-host.local/target"],
        attestation=True,
    )
    kwargs.update(overrides)
    return capture_consent(**kwargs)


def test_demo_scopes_pass():
    # Les 2 scopes utilisés en démo live DOIVENT passer la validation (beats 2 et 3).
    assert _capture(scope_urls=["https://mock-host.local/target"]).active
    assert _capture(scope_urls=["https://mock-host.local/minor-case"]).active


def test_unknown_role_rejected():
    with pytest.raises(ValueError):
        _capture(requester_role="stalker")


def test_missing_attestation_rejected():
    with pytest.raises(ConsentError):
        _capture(attestation=False)


def test_invalid_scopes_rejected():
    for bad in [[], ["https://host.tld/*"], ["/relative/path"], ["ftp://host.tld/x"]]:
        with pytest.raises(ValueError):
            _capture(scope_urls=bad)


def test_consent_artifact_written_and_verifiable(tmp_path, monkeypatch):
    # chdir vers tmp_path : les tests n'écrivent jamais de preuve dans le repo (public).
    monkeypatch.chdir(tmp_path)
    mandate = _capture()
    assert mandate.consent_artifact is not None
    assert mandate.consent_artifact.parent.name == ".mira_consent"
    assert mandate.consent_artifact.exists()
    assert verify_consent_artifact(mandate) is True


def test_tampered_consent_artifact_rejected(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mandate = _capture()
    data = json.loads(mandate.consent_artifact.read_text(encoding="utf-8"))
    # Falsification du payload : la signature HMAC ne colle plus -> preuve rejetée.
    data["payload_b64"] = base64.b64encode(b'{"forged": true}').decode("ascii")
    mandate.consent_artifact.write_text(json.dumps(data), encoding="utf-8")
    assert verify_consent_artifact(mandate) is False
