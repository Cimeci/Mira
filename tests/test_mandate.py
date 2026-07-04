"""Tests de capture_consent : le mandat ne peut pas exister sans consentement valide."""

import pytest

from mira.mandate import capture_consent
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
