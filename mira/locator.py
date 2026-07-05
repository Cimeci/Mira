"""Stage 1 — Le Locator. Trouve le média DANS le périmètre du mandat, uniquement.

Lane L1. Trois modes, choisis par `MIRA_LOCATOR_MODE` :
  - "mock"  (défaut) : candidat synthétique déterministe — démo stable (premortem T3),
                       tests hermétiques, skeleton stdlib qui tourne sans rien installé ;
  - "crawl"          : crawl Playwright pur (mira.cu.harvest) — récolte de VRAIES images
                       same-domain, rapide et déterministe : le chemin end-to-end fiable ;
  - "cu"             : crawler agentique Gemini Computer Use (mira.cu.crawler) — le vrai
                       Locator du pitch (live view), plus lent, nécessite une clé Gemini.

Dans TOUS les modes, G-2 est appliqué par du code, pas par une promesse : chaque candidat
passe par `is_in_scope` avant émission — hors-scope = rejeté et loggé, jamais mis en queue.
Les imports lourds (Playwright, google-genai) sont chargés PARESSEUSEMENT dans les modes
réels : le mode mock ne dépend que de la stdlib.
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import urlparse

from .events import Emit, make_event, print_emitter
from .types import Mandate, MediaItem, Status

# Génère un candidat hors-scope pour rendre le rejet G-2 visible en démo (beat 2).
SHOW_SCOPE_ENFORCEMENT = True
_OUT_OF_SCOPE_DECOY = "https://evil-mirror.example/leak.jpg"

# Mode du locator. Défaut PROD = "crawl" (récolte d'images RÉELLES, Playwright pur,
# déterministe). "cu" = crawler agentique Gemini (pitch/live view). "mock" = candidat
# synthétique, réservé aux tests hermétiques (conftest) et à la démo CLI stdlib
# (mira.demo, beats du premortem) — jamais le chemin de démo live.
_DEFAULT_MODE = "crawl"
_VALID_MODES = ("mock", "crawl", "cu")


def _mode() -> str:
    mode = os.getenv("MIRA_LOCATOR_MODE", _DEFAULT_MODE).strip().lower()
    if mode not in _VALID_MODES:
        # Fail-fast : un mode inconnu est une erreur de config, pas un fallback silencieux.
        raise ValueError(
            f"MIRA_LOCATOR_MODE invalide : {mode!r} (attendu : {', '.join(_VALID_MODES)})"
        )
    return mode


def _path_segments(path: str) -> list[str]:
    """Découpe un path en segments non vides (gère trailing slash et path vide)."""
    return [segment for segment in path.split("/") if segment]


def is_in_scope(candidate_url: str, scope_urls: list[str]) -> bool:
    """Vrai si l'URL candidate est couverte par au moins une URL de scope (G-2).

    Couverte = même scheme + même host (netloc exact, insensible à la casse) ET
    path candidat préfixe de SEGMENTS du scope : `/target-evil` ne matche pas un
    scope `/target`, mais `/target/sub/x.jpg` oui.
    """
    candidate = urlparse(candidate_url)
    candidate_segments = _path_segments(candidate.path)
    for scope_url in scope_urls:
        scope = urlparse(scope_url)
        if candidate.scheme.lower() != scope.scheme.lower():
            continue
        if candidate.netloc.lower() != scope.netloc.lower():
            continue
        scope_segments = _path_segments(scope.path)
        if candidate_segments[: len(scope_segments)] == scope_segments:
            return True
    return False


async def locate(
    mandate: Mandate,
    out: asyncio.Queue[MediaItem],
    *,
    log=print,
    emit: Emit = print_emitter,
) -> None:
    """Émet des MediaItem in-scope dans la queue partagée. Hors-scope = rejeté, jamais émis.

    Route vers le mode courant (`MIRA_LOCATOR_MODE`). Le contrat de sortie est identique
    dans les trois modes : un StageEvent LOCATED + un MediaItem par média in-scope.
    """
    # G-1 garanti en amont : orchestrator._require_active est le SEUL point de contrôle
    # (un assert ici serait strippé sous `python -O` — fausse sécurité).
    mode = _mode()
    if mode == "mock":
        candidates = _mock_candidates(mandate)
    else:
        candidates = await _harvest_real(mandate, mode=mode, log=log)
    await _emit_in_scope(mandate, candidates, out, log=log, emit=emit)


def _mock_candidates(mandate: Mandate) -> list[str]:
    """Candidats synthétiques déterministes (mode mock). Un in-scope par surface + un
    leurre hors-scope pour rendre le rejet G-2 visible en démo (beat 2)."""
    # rstrip évite `host//fichier` si le scope a un trailing slash.
    candidates = [f"{url.rstrip('/')}/synthetic_test.jpg" for url in mandate.scope_urls]
    if SHOW_SCOPE_ENFORCEMENT:
        candidates.append(_OUT_OF_SCOPE_DECOY)  # doit être rejeté, preuve vivante de G-2
    return candidates


async def _harvest_real(mandate: Mandate, *, mode: str, log) -> list[str]:
    """Récolte les URLs d'images RÉELLES sur les surfaces du mandat (modes crawl/cu).

    Imports paresseux : Playwright / google-genai ne sont chargés que sur ce chemin,
    jamais pour le mode mock (skeleton stdlib). Le filtrage in-scope est fait en aval
    par `_emit_in_scope` — ici on ne fait que récolter."""
    urls: list[str] = []
    for scope_url in mandate.scope_urls:
        start = _start_url(scope_url)
        if mode == "crawl":
            from .cu.harvest import crawl_images

            images = await crawl_images(start)
            urls.extend(img.url for img in images)
        else:  # "cu" — crawler agentique Gemini (peut échouer : clé absente, timeout)
            urls.extend(await _harvest_cu(start, log=log))
    log(
        f"[LOCATE/{mode}] {len(urls)} image(s) récoltée(s) "
        f"sur {len(mandate.scope_urls)} surface(s)"
    )
    return urls


def _start_url(scope_url: str) -> str:
    """Point de DÉPART du crawl. Par défaut = la surface du mandat elle-même.

    `MIRA_LOCATOR_START_URL` permet de démarrer DERRIÈRE un obstacle (un login JS,
    typiquement) tout en gardant le périmètre G-2 sur la surface consentie : le mock
    host de démo présente un login JS en page d'accueil, on démarre donc directement sur
    la galerie. Ça ne relâche RIEN — `is_in_scope` filtre chaque image récoltée en aval.
    Réglage mono-surface (démo) ; en prod la victime soumet directement l'URL de contenu."""
    return os.getenv("MIRA_LOCATOR_START_URL") or scope_url


async def _harvest_cu(scope_url: str, *, log) -> list[str]:
    """Consomme le flux du crawler agentique et renvoie les URLs d'images du run.

    Zéro silent failure : un event `error` du crawler (clé Gemini absente, sortie de
    périmètre…) devient une exception -> l'orchestrateur émet un FAILED locator propre,
    jamais un case vide sans explication."""
    from .cu.crawler import stream_crawl

    urls: list[str] = []
    async for ev in stream_crawl(scope_url):
        kind = ev.get("type")
        if kind == "error":
            raise RuntimeError(f"crawler agentique en échec : {ev.get('message')}")
        if kind == "done":
            urls.extend(img["url"] for img in ev.get("images", []))
        elif kind in ("page", "images", "links", "note", "safety"):
            log(f"[LOCATE/cu] {kind}: {ev.get('text') or ev.get('url') or ev.get('new') or ''}")
    return urls


async def _emit_in_scope(
    mandate: Mandate,
    candidates: list[str],
    out: asyncio.Queue[MediaItem],
    *,
    log,
    emit: Emit,
) -> None:
    """Émet UN LOCATED + MediaItem par candidat in-scope. Hors-scope = rejeté (G-2)."""
    emitted = 0
    for media_url in candidates:
        if not is_in_scope(media_url, mandate.scope_urls):
            # Pas une transition d'état (rien n'entre dans le pipeline) -> log, pas d'event.
            log(f"[LOCATE] hors-scope rejeté (G-2): {media_url}")
            continue
        emit(make_event(
            mandate.case_id,
            "locator",
            Status.LOCATED,
            from_status=Status.MANDATED,
            detail=f"[LOCATE] média in-scope trouvé : {media_url}",
            payload={"url": media_url},
        ))
        await out.put(MediaItem(case_id=mandate.case_id, url=media_url, status=Status.LOCATED))
        emitted += 1
        await asyncio.sleep(0)  # yield au runtime async
    if emitted == 0:
        log(f"[LOCATE] aucun média in-scope trouvé ({len(candidates)} candidat(s) évalué(s))")
