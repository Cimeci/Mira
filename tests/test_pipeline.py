"""Smoke tests du chemin de démo (spec G-13 : chaque stage testable avec mocks).

On teste UNE chose qui compte : les 3 beats de démo se comportent bien.
"""

import asyncio

from mira import mandate as mandate_mod
from mira.orchestrator import ConsentError, run
from mira.types import Status


def test_happy_path_dispatches_notice():
    m = mandate_mod.create_demo_mandate()
    results = asyncio.run(run(m, confirm=lambda notice: True))
    assert any(getattr(r, "status", None) is Status.NOTIFIED for r in results)


def test_no_active_mandate_refuses():
    m = mandate_mod.create_demo_mandate()
    m.active = False
    try:
        asyncio.run(run(m))
        assert False, "aurait dû refuser (ConsentError)"
    except ConsentError:
        pass


def test_suspected_minor_escalates_without_storage():
    m = mandate_mod.create_demo_mandate(case_id="minor")
    m.scope_urls = ["https://mock-host.local/minor-case"]
    results = asyncio.run(run(m, confirm=lambda notice: True))
    escalated = [r for r in results if getattr(r, "status", None) is Status.ESCALATED]
    assert escalated, "un flag mineur doit escalader"
    # Rien n'est stocké : pas de hash conservé.
    assert escalated[0].perceptual_hash == ""
    assert escalated[0].sha256_hash == ""


def test_victim_decline_holds_dispatch():
    m = mandate_mod.create_demo_mandate()
    results = asyncio.run(run(m, confirm=lambda notice: False))
    assert not any(getattr(r, "status", None) is Status.NOTIFIED for r in results)
