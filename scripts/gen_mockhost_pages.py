"""Génère le scénario de démo « protection de la victime » (mock host local, G-12).

Contexte : une personne a signalé UN média la représentant, publié sur un compte
tiers. Mira, sous mandat, explore ce compte À SA PLACE pour retrouver les AUTRES
médias — pour qu'elle n'ait pas à les chercher (et se re-traumatiser) elle-même.

  profil.html          → le compte signalé : grille de vignettes = des LIENS
  media/1.html … N.html → chaque média (l'image n'est révélée QU'en visitant la page)

Le crawler visite chaque lien ; la victime, elle, n'a rien à regarder. Sobre par
choix : placeholders neutres et abstraits, jamais de contenu réel.
Usage : .venv/bin/python scripts/gen_mockhost_pages.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "mira" / "mockhost"
N = 5

_STYLE = """<style>
:root { color-scheme: dark; }
* { box-sizing: border-box; }
body { margin:0; background:#0b0f14; color:#e6edf3;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
a { color:#2dd4bf; }
.flag { text-align:center; background:#2b1416; color:#fca5a5;
  border-bottom:1px solid #4c1d24; font-size:.82rem; padding:8px 16px; }
.wrap { max-width:960px; margin:26px auto 60px; padding:0 20px; }
.acct { display:flex; gap:14px; align-items:center; }
.avatar { width:64px; height:64px; border-radius:50%;
  background:linear-gradient(135deg,#3b1e2a,#6b7280); flex:0 0 auto; }
.acct h1 { font-size:1.15rem; margin:0; }
.acct .h { color:#7d8590; font-size:.9rem; }
.muted { color:#7d8590; font-size:.9rem; }
.grid { display:grid; gap:12px; margin-top:22px;
  grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); }
.thumb { display:block; text-decoration:none; color:inherit; }
.box { display:block; width:100%; aspect-ratio:1; border-radius:10px;
  background:linear-gradient(135deg,#1e2a3a,#334155); position:relative; }
.box::after { content:"média non affiché"; position:absolute; inset:0;
  display:grid; place-items:center; color:#64748b; font-size:.72rem; }
.thumb span { display:block; font-size:.78rem; color:#7d8590; margin-top:6px; }
.big { width:100%; max-width:520px; border-radius:14px;
  border:1px solid #1c2530; display:block; }
</style>"""

_PROFILE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>compte signalé — mock</title>
__STYLE__
</head><body>
<div class="flag">⚠ Compte faisant l'objet d'un signalement ·
exploration mandatée par la personne concernée</div>
<div class="wrap">
  <div class="acct">
    <div class="avatar"></div>
    <div>
      <h1>@compte_non_identifié</h1>
      <div class="h">__N__ médias publiés · la personne concernée n'en a vu qu'un</div>
    </div>
  </div>
  <p class="muted" style="margin-top:18px">Chaque vignette renvoie à la page du média
  (l'image n'y est révélée qu'en l'ouvrant). L'agent visite chaque page à la place de
  la victime.</p>
  <div class="grid">
__THUMBS__
  </div>
</div></body></html>
"""

_MEDIA = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>média __NN__ — compte signalé</title>
__STYLE__
</head><body>
<div class="flag">⚠ Média faisant l'objet du signalement</div>
<div class="wrap">
  <p><a href="../profil.html">← retour au compte</a></p>
  <h1 style="font-size:1.1rem">Média __NN__</h1>
  <img class="big" src="../images/img-__NN__.svg" alt="média __NN__" />
  <p class="muted" style="margin-top:14px">Placeholder abstrait · aucune donnée réelle.</p>
</div></body></html>
"""

_THUMB = (
    '<a class="thumb" href="media/__I__.html">'
    '<span class="box"></span>'
    "<span>média __NN__</span></a>"
)


def _apply(tpl: str, **kv: str) -> str:
    out = tpl.replace("__STYLE__", _STYLE)
    for key, val in kv.items():
        out = out.replace(f"__{key}__", val)
    return out


def main() -> None:
    (ROOT / "media").mkdir(parents=True, exist_ok=True)
    thumbs = "\n".join(
        _THUMB.replace("__I__", str(i)).replace("__NN__", f"{i:02d}") for i in range(1, N + 1)
    )
    (ROOT / "profil.html").write_text(
        _apply(_PROFILE, N=str(N), THUMBS=thumbs), encoding="utf-8"
    )
    for i in range(1, N + 1):
        (ROOT / "media" / f"{i}.html").write_text(
            _apply(_MEDIA, NN=f"{i:02d}"), encoding="utf-8"
        )
    print(f"✅ profil.html (compte signalé) + {N} pages média (media/1..{N}.html)")


if __name__ == "__main__":
    main()
