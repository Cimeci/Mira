"""Démo end-to-end (tout mocké, aucun réseau, aucun contenu réel) : `python -m mira.demo`.

Joue les 3 beats de démo du premortem :
  1) pas de mandat -> l'agent refuse
  2) pipeline complet -> notice DSA générée
  3) flag mineur -> halt + escalade, zéro stockage
"""

from __future__ import annotations

import asyncio

from . import mandate as mandate_mod
from .orchestrator import ConsentError, run
from .types import Status


def _banner(title: str) -> None:
    print(f"\n{'=' * 60}\n{title}\n{'=' * 60}")


async def main() -> None:
    # --- Beat 2 : happy path complet ---
    _banner("BEAT 2 — pipeline complet -> notice DSA")
    m = mandate_mod.create_demo_mandate()
    print(
        f"[MANDATE] case={m.case_id} role={m.requester_role} "
        f"active={m.active} scope={m.scope_urls}"
    )
    # confirm par défaut (_auto_confirm, async) : la CLI approuve immédiatement.
    results = await run(m)
    notice = next(
        (r.notice_text for r in results if isinstance(getattr(r, "notice_text", None), str)),
        None,
    )
    if notice:
        print("\n--- Notice générée (arrive dans l'inbox de démo) ---\n" + notice)

    # --- Beat 1 : refus sans mandat ---
    _banner("BEAT 1 — pas de mandat actif -> refus")
    mandate_mod.revoke(m)  # vraie révocation (active=False + horodatage), pas une mutation nue
    try:
        await run(m)
    except ConsentError as e:
        print(f"[REFUS] {e}")

    # --- Beat 3 : flag mineur -> halt + escalade ---
    _banner("BEAT 3 — mineur suspecté -> halt + escalade")
    m3 = mandate_mod.create_demo_mandate(case_id="demo-minor")
    m3.scope_urls = ["https://mock-host.local/minor-case"]
    results = await run(m3)
    escalated = any(r.status is Status.ESCALATED for r in results if hasattr(r, "status"))
    print(f"\n[RÉSULTAT] escaladé et arrêté sans stockage : {escalated}")


if __name__ == "__main__":
    asyncio.run(main())
