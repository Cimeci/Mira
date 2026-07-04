"""Tests de l'enforcement G-2 : is_in_scope + rejet à l'émission dans locate()."""

import asyncio

from mira.locator import is_in_scope, locate
from mira.mandate import create_demo_mandate

SCOPE = ["https://mock-host.local/target"]


def test_in_scope_accepted():
    assert is_in_scope("https://mock-host.local/target/synthetic_test.jpg", SCOPE)


def test_subpath_accepted():
    assert is_in_scope("https://mock-host.local/target/sub/deep/x.jpg", SCOPE)


def test_different_host_rejected():
    assert not is_in_scope("https://evil-mirror.example/target/x.jpg", SCOPE)


def test_sibling_path_rejected():
    # Préfixe de SEGMENT, pas de chaîne : /target-evil ne doit pas matcher /target.
    assert not is_in_scope("https://mock-host.local/target-evil/x.jpg", SCOPE)


def test_trailing_slash_handled():
    assert is_in_scope("https://mock-host.local/target/x.jpg", ["https://mock-host.local/target/"])
    assert is_in_scope("https://mock-host.local/target/", SCOPE)


def test_host_case_insensitive():
    assert is_in_scope("https://MOCK-HOST.local/target/x.jpg", SCOPE)


def test_locate_never_emits_out_of_scope():
    # Le leurre hors-scope (SHOW_SCOPE_ENFORCEMENT) doit être rejeté, jamais mis en queue.
    m = create_demo_mandate()
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.run(locate(m, queue, log=lambda *_: None))
    emitted = []
    while not queue.empty():
        emitted.append(queue.get_nowait())
    assert emitted, "le média in-scope doit être émis"
    for item in emitted:
        assert is_in_scope(item.url, m.scope_urls), f"hors-scope émis : {item.url}"
