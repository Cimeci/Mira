"""Génère les images placeholder du mock host (galerie de démo).

Tuiles SVG neutres (dégradé + numéro) — AUCUN contenu réel, conforme G-12.
Rejouable : écrase mira/mockhost/images/img-01.svg .. img-12.svg.

Usage : .venv/bin/python scripts/gen_mockhost_images.py
"""

from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "mira" / "mockhost" / "images"
COUNT = 12

# Paires (couleur haut-gauche, couleur bas-droite) — palette tech neutre.
PALETTE = [
    ("#0f2942", "#2dd4bf"), ("#1e1b4b", "#a78bfa"), ("#3b0d1f", "#fb7185"),
    ("#0d2818", "#4ade80"), ("#2b1d02", "#fbbf24"), ("#0a2233", "#38bdf8"),
    ("#1a1030", "#c084fc"), ("#022c22", "#34d399"), ("#2d0a12", "#f472b6"),
    ("#0c1d3a", "#60a5fa"), ("#241804", "#facc15"), ("#111827", "#94a3b8"),
]

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg"
     width="640" height="640" viewBox="0 0 640 640">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{c0}"/>
      <stop offset="1" stop-color="{c1}"/>
    </linearGradient>
  </defs>
  <rect width="640" height="640" fill="url(#g)"/>
  <text x="50%" y="47%" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="150" font-weight="700" fill="rgba(255,255,255,.9)"
        text-anchor="middle" dominant-baseline="central">{n:02d}</text>
  <text x="50%" y="84%" font-family="ui-monospace, SFMono-Regular, Menlo, monospace"
        font-size="26" letter-spacing="4" fill="rgba(255,255,255,.55)"
        text-anchor="middle">MOCK · SAMPLE</text>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(1, COUNT + 1):
        c0, c1 = PALETTE[(i - 1) % len(PALETTE)]
        (OUT / f"img-{i:02d}.svg").write_text(
            TEMPLATE.format(c0=c0, c1=c1, n=i), encoding="utf-8"
        )
    print(f"✅ {COUNT} tuiles générées dans {OUT}")


if __name__ == "__main__":
    main()
