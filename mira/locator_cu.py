"""Stage 1 RÉEL — Locator « computer use » (Gemini 2.5 CU = cerveau, Playwright = bras).

Lane L1. Implémente le moteur décrit dans ARCHITECTURE.md §2 :

    requête + screenshot + historique
                │
                ▼
       Gemini 2.5 Computer Use  → action (clic/frappe/scroll) ou demande de confirmation
                │
                ▼
       Playwright (Chromium)    → exécute l'action, reprend un screenshot
                │
                ▼
       nouveau screenshot renvoyé au modèle → on reboucle jusqu'à done / halt

CE QUI EST NON-NÉGOCIABLE ICI (guardrails déjà en place ailleurs, on ne les affaiblit pas) :
  - G-2 : chaque URL candidate (navigation OU média extrait) passe par
    `locator.is_in_scope(url, mandate.scope_urls)` AVANT toute navigation/émission.
    On IMPORTE `is_in_scope`, on ne le réimplémente pas. Un candidat hors-scope construit
    par le LLM est refusé et loggé — il n'entre JAMAIS dans la queue de sortie.
  - Read-only strict : pas de login, pas de submit, on ne suit AUCUN lien hors scope.
    Toute action jugée « à risque » par Gemini (submit/login/paiement…) est DÉCLINÉE.
  - G-6 / G-5 : on ne récupère que des RÉFÉRENCES (URLs). Le download des octets reste
    différé à l'analyzer, APRÈS son pré-check mineur. On ne télécharge/hash/stocke rien ici.

FIABILITÉ (ARCHITECTURE.md §2.5) : timeouts + backoff sur chaque I/O, watchdog qui tue une
session bloquée (`asyncio.wait_for` sur le budget global), pruning des vieux screenshots du
contexte Gemini. Toute erreur réseau/API/navigateur retombe proprement sur le mock
déterministe (`locator._locate_mock`) — jamais un crash qui bloque la démo.

────────────────────────────────────────────────────────────────────────────────────────
GO / NO-GO (décision d'équipe ce soir) — critère écrit noir sur blanc :

  « navigue de façon fiable sur le mock host » ==
    `GO_NOGO_TRIALS` (=3) exécutions CONSÉCUTIVES de `locate_real` contre le mock host
    de démo qui, CHACUNE et SANS intervention manuelle :
      1. terminent en moins de `GO_NOGO_MAX_SECONDS` (=90 s) ;
      2. émettent AU MOINS un média in-scope dans la queue ;
      3. émettent ZÉRO média hors-scope ;
      4. n'ont PAS eu besoin du filet mock (aucun fallback déclenché).

  3/3 réussies  → GO  : la brique reste dans le chemin de démo live.
  < 3/3         → NO-GO : on sort la nav live du live (vidéo pré-enregistrée + mock en
                          direct), SANS débat ni prolongation.

  Harnais exécutable :  MIRA_LOCATOR_REAL=1 python -m mira.locator_cu --url <mock-host-url>
  (nécessite : une clé Gemini/Vertex, `pip install google-genai playwright`,
   `playwright install chromium`, et un mock host RÉELLEMENT joignable — cf. mock_host/).
────────────────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import urljoin

from .events import Emit, make_event, print_emitter
from .locator import _locate_mock, is_in_scope  # is_in_scope = point d'enforcement G-2 unique
from .types import Mandate, MediaItem, Status

# ── Paramètres de fiabilité (surchargables par env pour le tuning terrain) ─────────────
MODEL_ID = os.getenv("MIRA_GEMINI_CU_MODEL", "gemini-2.5-computer-use-preview-10-2025")
STEP_TIMEOUT_S = float(os.getenv("MIRA_CU_STEP_TIMEOUT_S", "25"))       # une I/O modèle/nav
SESSION_BUDGET_S = float(os.getenv("MIRA_CU_SESSION_BUDGET_S", "120"))  # watchdog global anti-stall
MAX_STEPS = int(os.getenv("MIRA_CU_MAX_STEPS", "24"))                   # borne dure de la boucle
MAX_RETRIES = int(os.getenv("MIRA_CU_MAX_RETRIES", "3"))               # backoff par appel
BACKOFF_BASE_S = float(os.getenv("MIRA_CU_BACKOFF_BASE_S", "0.5"))
CONTEXT_SCREENSHOT_WINDOW = int(os.getenv("MIRA_CU_SCREENSHOT_WINDOW", "3"))  # pruning contexte
MAX_SCOPE_REFUSALS = int(os.getenv("MIRA_CU_MAX_SCOPE_REFUSALS", "4"))  # anti-boucle hors-scope

# Critère go/no-go (voir docstring). Constantes = contrat, pas de la magie enfouie.
GO_NOGO_TRIALS = 3
GO_NOGO_MAX_SECONDS = 90.0


# ── Contrats internes : cerveau / bras injectables (⇒ testables sans clé ni navigateur) ─
@dataclass
class ProposedAction:
    """Décision normalisée du cerveau à une étape de la boucle."""

    done: bool = False                       # le modèle estime la tâche finie
    navigate_to: str | None = None           # URL que le modèle veut ouvrir (soumise à G-2)
    interaction: dict | None = None           # action UI opaque à passer au bras (clic/scroll…)
    risky: bool = False                       # action « à risque » (submit/login) → déclinée
    raw_name: str = ""                        # nom brut de l'action (trace)


class Brain(Protocol):
    """Le cerveau : décide l'action UI suivante à partir du screenshot courant."""

    async def next_action(
        self, *, goal: str, screenshot: bytes, url: str, step: int
    ) -> ProposedAction: ...


class Arm(Protocol):
    """Le bras : exécute réellement les actions et lit l'état du navigateur (read-only)."""

    async def goto(self, url: str) -> None: ...
    async def act(self, interaction: dict) -> None: ...
    async def screenshot(self) -> bytes: ...
    async def current_url(self) -> str: ...
    async def extract_media_urls(self) -> list[str]: ...  # srcs <img>/<video>, absolus
    async def close(self) -> None: ...


@dataclass
class LocateOutcome:
    """Résultat d'une session de navigation réelle (sert au harnais go/no-go)."""

    in_scope_urls: list[str] = field(default_factory=list)
    out_of_scope_refused: int = 0
    steps: int = 0
    used_fallback: bool = False
    error: str | None = None


# ── Utilitaires de fiabilité ──────────────────────────────────────────────────────────
async def _with_retries(func, *args, what: str, log, **kwargs) -> object:
    """Appelle `func(*args, **kwargs)` (coroutine) avec timeout + backoff exponentiel.

    Ré-lève après MAX_RETRIES. On appelle `func` à NEUF à chaque essai (une coroutine n'est
    awaitable qu'une fois). Pas de bare `except` : on attrape explicitement `Exception` (toute
    I/O réseau/navigateur), on la logge, et on la relaie si les essais sont épuisés —
    l'appelant décide alors du fallback.
    """
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=STEP_TIMEOUT_S)
        except asyncio.CancelledError:
            raise  # annulation (watchdog) = on remonte, jamais avalée
        except Exception as exc:  # noqa: BLE001 — attrapé explicitement, loggé, puis relayé
            last_exc = exc
            log(f"[LOCATE-CU] {what} échec {attempt}/{MAX_RETRIES} ({type(exc).__name__})")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(BACKOFF_BASE_S * (2 ** (attempt - 1)))
    assert last_exc is not None
    raise last_exc


# ── Cœur : la boucle Computer Use, PURE (indépendante du SDK réel → testée avec des fakes) ─
async def run_cu_loop(
    mandate: Mandate,
    brain: Brain,
    arm: Arm,
    *,
    log=print,
) -> LocateOutcome:
    """Boucle screenshot→décision→action jusqu'à done/halt. Renvoie les RÉFÉRENCES in-scope.

    N'ÉMET NI NE MET RIEN EN QUEUE : elle se contente de collecter des URLs média in-scope.
    L'émission (events + queue) est faite par `locate_real` APRÈS une session réussie, pour
    garantir une sémantique atomique (aucun doublon avec le fallback mock).

    G-2 appliqué à DEUX endroits, tous deux via `is_in_scope` :
      - une navigation proposée vers une URL hors-scope est REFUSÉE (jamais suivie) ;
      - un média extrait hors-scope est JETÉ (jamais ajouté au résultat).
    """
    outcome = LocateOutcome()
    goal = (
        "Tu es un agent READ-ONLY. Explore uniquement les pages du périmètre autorisé pour "
        "révéler les médias images/vidéos présents (scroll, 'charger plus'). Ne te connecte "
        "PAS, ne soumets AUCUN formulaire, ne suis AUCUN lien hors du périmètre. "
        f"Périmètre autorisé : {mandate.scope_urls}."
    )
    seen: set[str] = set()

    def _harvest(current_url: str, raw_media: list[str]) -> None:
        """Absolutise puis filtre G-2 les médias de la page courante. Hors-scope = jeté + loggé."""
        for raw in raw_media:
            absolute = urljoin(current_url, raw)
            if absolute in seen:
                continue
            seen.add(absolute)
            if is_in_scope(absolute, mandate.scope_urls):
                outcome.in_scope_urls.append(absolute)
            else:
                # Un média présent dans le DOM mais hors périmètre : jamais retenu.
                outcome.out_of_scope_refused += 1
                log(f"[LOCATE-CU] média hors-scope jeté (G-2): {absolute}")

    # Entrée : la 1re URL de scope. Garde-fou : elle DOIT être in-scope (elle l'est par
    # construction, mais on ne fait pas confiance — is_in_scope tranche).
    entry = mandate.scope_urls[0]
    if not is_in_scope(entry, mandate.scope_urls):
        raise ValueError("URL d'entrée hors de son propre scope — mandat incohérent (G-2).")
    await _with_retries(arm.goto, entry, what="goto(entry)", log=log)

    for step in range(1, MAX_STEPS + 1):
        outcome.steps = step
        shot = await _with_retries(arm.screenshot, what="screenshot", log=log)
        url = await _with_retries(arm.current_url, what="current_url", log=log)
        _harvest(url, await _with_retries(arm.extract_media_urls, what="extract_media", log=log))

        action = await _with_retries(
            brain.next_action,
            what="brain.next_action",
            log=log,
            goal=goal,
            screenshot=shot,
            url=url,
            step=step,
        )

        if action.done:
            log(f"[LOCATE-CU] modèle: tâche finie à l'étape {step}")
            break
        if action.risky:
            # Read-only : toute action à risque (login/submit) est déclinée, jamais exécutée.
            log(f"[LOCATE-CU] action à risque déclinée (read-only): {action.raw_name}")
            break
        if action.navigate_to is not None:
            if not is_in_scope(action.navigate_to, mandate.scope_urls):
                # LE cas critique : le LLM veut sortir du scope → refus dur, on ne navigue pas.
                outcome.out_of_scope_refused += 1
                log(f"[LOCATE-CU] navigation hors-scope refusée (G-2): {action.navigate_to}")
                if outcome.out_of_scope_refused >= MAX_SCOPE_REFUSALS:
                    log("[LOCATE-CU] trop de tentatives hors-scope — arrêt de la session.")
                    break
                continue
            await _with_retries(arm.goto, action.navigate_to, what="goto", log=log)
        elif action.interaction is not None:
            await _with_retries(arm.act, action.interaction, what="act", log=log)
        else:
            log("[LOCATE-CU] action vide — arrêt.")
            break

    return outcome


# ── Adaptateurs RÉELS (google-genai + Playwright). Non exécutés par les tests. ──────────
class GeminiBrain:
    """Cerveau réel : Gemini 2.5 Computer Use via le SDK google-genai (Vertex ou AI Studio).

    Maintient l'historique `contents` (screenshots + actions) et le PRUNE pour borner le
    budget tokens sur les longues sessions (ARCHITECTURE.md §2.5) : on ne garde que les
    `CONTEXT_SCREENSHOT_WINDOW` derniers screenshots, les plus vieux sont remplacés par un
    marqueur texte. Le context caching Gemini reste un levier simple à brancher ensuite
    (config.cached_content) — non câblé ici pour ne pas sur-optimiser avant le go/no-go.

    ⚠️ Le catalogue exact des actions prédéfinies de `gemini-2.5-computer-use` peut évoluer ;
    `_normalize` mappe les noms courants (open_web_page/navigate, click_at, type_text_at,
    scroll_document…) vers `ProposedAction`. À revérifier contre la doc Google au moment du
    test réel — d'où le go/no-go exécutable plutôt qu'une confiance aveugle.
    """

    # Actions considérées « à risque » → déclinées en read-only (login/submit/paiement).
    _RISKY = {"submit", "login", "type_password", "purchase", "confirm_payment"}
    # Actions qui portent une URL de navigation (soumises à G-2 par la boucle).
    _NAV = {"open_web_page", "navigate", "go_to_url"}

    def __init__(self, *, mandate: Mandate) -> None:
        # Imports différés : n'exigent google-genai QUE sur le chemin réel.
        from google import genai
        from google.genai import types

        self._types = types
        # Vertex AI si configuré (même cloud que Cloud Run — clé/réseau alignés), sinon
        # AI Studio (GEMINI_API_KEY / GOOGLE_API_KEY). Le SDK lit l'env tout seul.
        if os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() not in {"", "0", "false"}:
            self._client = genai.Client(vertexai=True)
        else:
            self._client = genai.Client()
        self._tool = types.Tool(
            computer_use=types.ComputerUse(
                environment=types.Environment.ENVIRONMENT_BROWSER,
                # On coupe les actions dangereuses côté modèle en plus du refus côté boucle.
                excluded_predefined_functions=sorted(self._RISKY),
            )
        )
        self._config = types.GenerateContentConfig(tools=[self._tool])
        self._contents: list = []
        self._mandate = mandate

    def _prune(self) -> None:
        """Ne conserve que les N derniers screenshots (le reste → marqueur texte)."""
        shots = [i for i, c in enumerate(self._contents) if _has_inline_image(c)]
        for idx in shots[:-CONTEXT_SCREENSHOT_WINDOW]:
            self._contents[idx] = self._types.Content(
                role="user",
                parts=[self._types.Part.from_text(text="[screenshot élagué — contexte borné]")],
            )

    def _normalize(self, fc) -> ProposedAction:
        name = (getattr(fc, "name", "") or "").lower()
        args = dict(getattr(fc, "args", {}) or {})
        if name in self._RISKY:
            return ProposedAction(risky=True, raw_name=name)
        if name in self._NAV:
            return ProposedAction(navigate_to=args.get("url") or args.get("href"), raw_name=name)
        return ProposedAction(interaction={"name": name, "args": args}, raw_name=name)

    async def next_action(
        self, *, goal: str, screenshot: bytes, url: str, step: int
    ) -> ProposedAction:
        types = self._types
        parts = [types.Part.from_bytes(data=screenshot, mime_type="image/png")]
        if step == 1:
            parts.insert(0, types.Part.from_text(text=f"{goal}\nURL courante : {url}"))
        else:
            parts.insert(0, types.Part.from_text(text=f"URL courante : {url}"))
        self._contents.append(types.Content(role="user", parts=parts))
        self._prune()
        # generate_content est synchrone dans le SDK → on le déporte hors de la boucle event.
        response = await asyncio.to_thread(
            self._client.models.generate_content,
            model=MODEL_ID,
            contents=self._contents,
            config=self._config,
        )
        candidate = response.candidates[0]
        self._contents.append(candidate.content)
        calls = getattr(response, "function_calls", None) or []
        if not calls:
            return ProposedAction(done=True, raw_name="text_final")
        return self._normalize(calls[0])


def _has_inline_image(content) -> bool:
    """Vrai si un Content transporte une image inline (pour cibler le pruning)."""
    for part in getattr(content, "parts", []) or []:
        blob = getattr(part, "inline_data", None)
        if blob is not None and str(getattr(blob, "mime_type", "")).startswith("image/"):
            return True
    return False


class PlaywrightArm:
    """Bras réel : Chromium piloté par Playwright, read-only. À instancier via `create`."""

    def __init__(self, playwright, browser, page) -> None:
        self._pw = playwright
        self._browser = browser
        self._page = page

    @classmethod
    async def create(cls) -> PlaywrightArm:
        # Import différé : n'exige playwright QUE sur le chemin réel.
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        # Sandbox : dans le container Cloud Run/Browserbase (§4), headless, egress restreint.
        browser = await pw.chromium.launch(headless=True)
        page = await browser.new_page()
        return cls(pw, browser, page)

    async def goto(self, url: str) -> None:
        # wait_until="domcontentloaded" : on ne bloque pas sur des trackers lents.
        await self._page.goto(url, wait_until="domcontentloaded", timeout=STEP_TIMEOUT_S * 1000)

    async def act(self, interaction: dict) -> None:
        name = interaction.get("name", "")
        args = interaction.get("args", {})
        # Sous-ensemble read-only : scroll + attente. Clics/frappes réels sont branchés ici
        # au moment du test réel (page.mouse.click(x, y), page.keyboard.type…), jamais un submit.
        if name in {"scroll_document", "scroll", "scroll_at"}:
            await self._page.mouse.wheel(0, int(args.get("dy", 800)))
        elif name in {"wait_5_seconds", "wait"}:
            await asyncio.sleep(min(5.0, float(args.get("seconds", 1))))
        # Toute autre action non whitelistée est un no-op sûr (on ne devine pas un geste risqué).

    async def screenshot(self) -> bytes:
        return await self._page.screenshot(type="png")

    async def current_url(self) -> str:
        return self._page.url

    async def extract_media_urls(self) -> list[str]:
        # On ne récupère que des RÉFÉRENCES (srcs), jamais les octets (G-5/G-6).
        return await self._page.eval_on_selector_all(
            "img, video, source",
            "els => els.map(e => e.currentSrc || e.src).filter(Boolean)",
        )

    async def close(self) -> None:
        # Teardown best-effort : une erreur de fermeture ne doit pas masquer le résultat.
        for closer in (self._browser.close, self._pw.stop):
            try:
                await closer()
            except Exception:  # noqa: BLE001 — cleanup, on log rien de plus qu'un best-effort
                pass


# ── Point d'entrée réel : câble brain+arm, applique le watchdog, émet, retombe sur le mock ─
async def locate_real(
    mandate: Mandate,
    out: asyncio.Queue[MediaItem],
    *,
    log=print,
    emit: Emit = print_emitter,
    brain: Brain | None = None,
    arm: Arm | None = None,
) -> None:
    """Locator RÉEL. Émet les MediaItem in-scope trouvés par la navigation Computer Use.

    Sur TOUTE erreur (deps absentes, clé manquante, réseau, navigateur, watchdog) : log clair
    + fallback déterministe sur `_locate_mock`. La démo n'est jamais bloquée par cette brique.
    `brain`/`arm` injectables pour les tests ; en prod ils sont construits ici (deps lourdes).
    """
    outcome = await _run_real_session(mandate, log=log, brain=brain, arm=arm)

    if outcome.used_fallback or not outcome.in_scope_urls:
        # Échec réel OU rien trouvé : on ne laisse pas la victime avec une queue vide.
        reason = outcome.error or "aucun média in-scope trouvé"
        log(f"[LOCATE-CU] fallback mock déterministe ({reason})")
        await _locate_mock(mandate, out, log=log, emit=emit)
        return

    # Session réussie : émission atomique des références in-scope (dédupliquées).
    for media_url in outcome.in_scope_urls:
        emit(make_event(
            mandate.case_id,
            "locator",
            Status.LOCATED,
            from_status=Status.MANDATED,
            detail=f"[LOCATE] média in-scope trouvé (computer use) : {media_url}",
            payload={"url": media_url},
        ))
        await out.put(MediaItem(case_id=mandate.case_id, url=media_url, status=Status.LOCATED))
        await asyncio.sleep(0)


async def _run_real_session(
    mandate: Mandate,
    *,
    log=print,
    brain: Brain | None = None,
    arm: Arm | None = None,
) -> LocateOutcome:
    """Construit (au besoin) brain+arm, lance la boucle sous watchdog, garantit le teardown.

    Ne lève jamais : encapsule toute erreur dans `LocateOutcome(used_fallback=True, error=…)`.
    """
    owns_arm = arm is None
    try:
        if brain is None:
            brain = GeminiBrain(mandate=mandate)
        if arm is None:
            arm = await asyncio.wait_for(PlaywrightArm.create(), timeout=STEP_TIMEOUT_S)
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — deps/clé absentes ⇒ fallback, pas un crash
        return LocateOutcome(used_fallback=True, error=f"init {type(exc).__name__}: {exc}")

    try:
        # Watchdog : le budget global tue une session bloquée (une boucle qui pend).
        outcome = await asyncio.wait_for(
            run_cu_loop(mandate, brain, arm, log=log), timeout=SESSION_BUDGET_S
        )
        return outcome
    except TimeoutError:
        log("[LOCATE-CU] watchdog: session tuée (budget dépassé).")
        return LocateOutcome(used_fallback=True, error="watchdog timeout")
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 — toute panne nav/API ⇒ fallback déterministe
        return LocateOutcome(used_fallback=True, error=f"{type(exc).__name__}: {exc}")
    finally:
        if owns_arm and arm is not None:
            await arm.close()


# ── Harnais go/no-go exécutable (voir critère en tête de module) ────────────────────────
async def _go_nogo(entry_url: str) -> int:
    """Lance GO_NOGO_TRIALS sessions réelles contre `entry_url` et imprime le verdict."""
    from . import mandate as mandate_mod

    m = mandate_mod.create_demo_mandate(case_id="go-nogo")
    m.scope_urls = [entry_url]  # on teste le VRAI mock host fourni, pas mock-host.local

    loop = asyncio.get_event_loop()
    passes = 0
    for trial in range(1, GO_NOGO_TRIALS + 1):
        queue: asyncio.Queue[MediaItem] = asyncio.Queue()
        started = loop.time()
        outcome = await _run_real_session(m, log=print)
        elapsed = loop.time() - started
        for u in outcome.in_scope_urls:
            await queue.put(MediaItem(case_id=m.case_id, url=u))
        ok = (
            not outcome.used_fallback
            and outcome.in_scope_urls
            and outcome.out_of_scope_refused == 0
            and elapsed < GO_NOGO_MAX_SECONDS
        )
        passes += 1 if ok else 0
        print(
            f"[GO/NO-GO] essai {trial}/{GO_NOGO_TRIALS}: "
            f"{'OK' if ok else 'ÉCHEC'} — {len(outcome.in_scope_urls)} in-scope, "
            f"{outcome.out_of_scope_refused} hors-scope refusés, "
            f"fallback={outcome.used_fallback}, {elapsed:.1f}s"
            + (f", err={outcome.error}" if outcome.error else "")
        )
    verdict = "GO" if passes == GO_NOGO_TRIALS else "NO-GO"
    print(f"\n=== {verdict} === ({passes}/{GO_NOGO_TRIALS} essais réussis)")
    return 0 if verdict == "GO" else 1


def main() -> int:
    """`MIRA_LOCATOR_REAL=1 python -m mira.locator_cu --url <mock-host-url>`."""
    import sys

    url = os.getenv("MIRA_LOCATOR_TEST_URL")
    argv = sys.argv[1:]
    if "--url" in argv:
        url = argv[argv.index("--url") + 1]
    if not url:
        print("usage: python -m mira.locator_cu --url <mock-host-url>  (ou MIRA_LOCATOR_TEST_URL)")
        print("       nécessite une clé Gemini/Vertex + `pip install google-genai playwright`")
        print("       + `playwright install chromium`, et un mock host joignable.")
        return 2
    return asyncio.run(_go_nogo(url))


if __name__ == "__main__":
    raise SystemExit(main())
