"""Tests du Locator RÉEL (computer use) — SANS google-genai, SANS navigateur, SANS clé.

On injecte un cerveau (`Brain`) et un bras (`Arm`) factices dans `run_cu_loop` /
`locate_real` : ça teste la LOGIQUE de la boucle et surtout l'enforcement G-2 du chemin
réel de façon déterministe. Le point qui compte le plus (un candidat hors-scope construit
par le LLM ne doit JAMAIS entrer dans la queue de sortie) est couvert explicitement.
"""

import asyncio

import pytest

from mira import locator_cu
from mira.locator import is_in_scope
from mira.locator_cu import ProposedAction, locate_real, run_cu_loop
from mira.mandate import create_demo_mandate
from mira.types import MediaItem

SCOPE = ["https://mock-host.local/target"]
IN_SCOPE_MEDIA = "https://mock-host.local/target/photo.jpg"
OUT_OF_SCOPE_MEDIA = "https://evil-mirror.example/leak.jpg"
OUT_OF_SCOPE_PAGE = "https://evil-mirror.example/hack"


class FakeArm:
    """Bras factice : sert des médias scriptés par URL, journalise les navigations."""

    def __init__(self, media_by_url, *, fail_on=None):
        self._media_by_url = media_by_url
        self._fail_on = fail_on or set()
        self._current = None
        self.visited = []
        self.acted = []
        self.closed = False

    async def goto(self, url):
        if "goto" in self._fail_on:
            raise RuntimeError("boom goto")
        self.visited.append(url)
        self._current = url

    async def act(self, interaction):
        self.acted.append(interaction)

    async def screenshot(self):
        if "screenshot" in self._fail_on:
            raise RuntimeError("boom screenshot")
        return b"\x89PNG-fake"

    async def current_url(self):
        return self._current or SCOPE[0]

    async def extract_media_urls(self):
        return list(self._media_by_url.get(self._current, []))

    async def close(self):
        self.closed = True


class ScriptedBrain:
    """Cerveau factice : renvoie une action scriptée par étape, puis `done`."""

    def __init__(self, actions):
        self._actions = list(actions)

    async def next_action(self, *, goal, screenshot, url, step):
        if self._actions:
            return self._actions.pop(0)
        return ProposedAction(done=True, raw_name="done")


def _drain(queue):
    out = []
    while not queue.empty():
        out.append(queue.get_nowait())
    return out


def test_in_scope_media_emitted():
    """Happy path : un média in-scope trouvé par la nav réelle est émis dans la queue."""
    m = create_demo_mandate()
    arm = FakeArm({SCOPE[0]: [IN_SCOPE_MEDIA, OUT_OF_SCOPE_MEDIA]})
    brain = ScriptedBrain([ProposedAction(interaction={"name": "scroll_document"})])
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.run(locate_real(m, queue, log=lambda *_: None, brain=brain, arm=arm))
    emitted = _drain(queue)
    assert [i.url for i in emitted] == [IN_SCOPE_MEDIA]
    assert arm.closed is False  # arm injecté = non possédé, on ne le ferme pas


def test_out_of_scope_media_never_emitted():
    """Un média hors-scope présent dans le DOM est JETÉ, jamais mis en queue (G-2)."""
    m = create_demo_mandate()
    arm = FakeArm({SCOPE[0]: [OUT_OF_SCOPE_MEDIA]})
    brain = ScriptedBrain([])  # done immédiat
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.run(locate_real(m, queue, log=lambda *_: None, brain=brain, arm=arm))
    emitted = _drain(queue)
    for item in emitted:
        assert is_in_scope(item.url, m.scope_urls), f"hors-scope émis : {item.url}"
    # Rien d'in-scope trouvé -> fallback mock déterministe, jamais l'URL hostile.
    assert OUT_OF_SCOPE_MEDIA not in [i.url for i in emitted]


def test_llm_out_of_scope_navigation_refused():
    """LE cas critique : le LLM demande d'ouvrir une URL hors-scope -> jamais navigué/émis."""
    m = create_demo_mandate()
    arm = FakeArm({SCOPE[0]: [IN_SCOPE_MEDIA]})
    brain = ScriptedBrain([ProposedAction(navigate_to=OUT_OF_SCOPE_PAGE, raw_name="open_web_page")])
    outcome = asyncio.run(run_cu_loop(m, brain, arm, log=lambda *_: None))
    # Le bras n'a JAMAIS visité l'URL hors-scope (seule l'entrée in-scope).
    assert OUT_OF_SCOPE_PAGE not in arm.visited
    assert arm.visited == [SCOPE[0]]
    assert outcome.out_of_scope_refused >= 1
    # Et seul le média in-scope est remonté comme référence.
    assert outcome.in_scope_urls == [IN_SCOPE_MEDIA]


def test_risky_action_declined_read_only():
    """Une action à risque (submit/login) est déclinée : jamais exécutée par le bras."""
    m = create_demo_mandate()
    arm = FakeArm({SCOPE[0]: [IN_SCOPE_MEDIA]})
    brain = ScriptedBrain([ProposedAction(risky=True, raw_name="submit")])
    outcome = asyncio.run(run_cu_loop(m, brain, arm, log=lambda *_: None))
    assert arm.acted == []  # aucune action UI exécutée
    assert outcome.in_scope_urls == [IN_SCOPE_MEDIA]


def test_navigation_failure_falls_back_to_mock():
    """Erreur navigateur -> fallback déterministe sur le mock (jamais un crash)."""
    m = create_demo_mandate()
    arm = FakeArm({}, fail_on={"screenshot"})
    brain = ScriptedBrain([])
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.run(locate_real(m, queue, log=lambda *_: None, brain=brain, arm=arm))
    emitted = _drain(queue)
    # Le mock émet le candidat synthétique in-scope.
    assert any(i.url.endswith("/target/synthetic_test.jpg") for i in emitted)
    for item in emitted:
        assert is_in_scope(item.url, m.scope_urls)


def test_watchdog_kills_stalled_session(monkeypatch):
    """Watchdog : une session bloquée est tuée sous le budget, puis fallback mock."""

    class HangingArm(FakeArm):
        async def goto(self, url):
            await asyncio.sleep(5)  # simule une nav qui pend

    monkeypatch.setattr(locator_cu, "SESSION_BUDGET_S", 0.05)
    m = create_demo_mandate()
    arm = HangingArm({SCOPE[0]: [IN_SCOPE_MEDIA]})
    brain = ScriptedBrain([])
    queue: asyncio.Queue = asyncio.Queue()
    asyncio.run(locate_real(m, queue, log=lambda *_: None, brain=brain, arm=arm))
    emitted = _drain(queue)
    # Session tuée -> on ne bloque pas : le mock déterministe prend le relais.
    assert any(i.url.endswith("/target/synthetic_test.jpg") for i in emitted)


@pytest.mark.parametrize(
    "real,demo,expected",
    [
        (None, None, False),   # rien -> mock
        ("1", None, True),     # réel activé
        ("true", None, True),
        ("0", None, False),    # explicitement désactivé
        ("1", "1", False),     # mode démo FORCE le mock, même si réel demandé
    ],
)
def test_real_locator_flag(monkeypatch, real, demo, expected):
    from mira import locator

    monkeypatch.delenv("MIRA_LOCATOR_REAL", raising=False)
    monkeypatch.delenv("MIRA_DEMO_MODE", raising=False)
    if real is not None:
        monkeypatch.setenv("MIRA_LOCATOR_REAL", real)
    if demo is not None:
        monkeypatch.setenv("MIRA_DEMO_MODE", demo)
    assert locator._real_locator_enabled() is expected


def test_dispatcher_uses_mock_when_disabled(monkeypatch):
    """Flag off : locate() reste 100 % mock, aucune dépendance lourde requise."""
    from mira.locator import locate

    monkeypatch.delenv("MIRA_LOCATOR_REAL", raising=False)
    m = create_demo_mandate()
    queue: asyncio.Queue[MediaItem] = asyncio.Queue()
    asyncio.run(locate(m, queue, log=lambda *_: None))
    emitted = _drain(queue)
    assert emitted and all(is_in_scope(i.url, m.scope_urls) for i in emitted)
