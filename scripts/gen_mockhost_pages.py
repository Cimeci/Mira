"""Génère la structure 2-niveaux du mock host (banc de test du crawler).

  gallery.html          → grille de vignettes, chacune un LIEN vers une page photo
  photo/1.html … N.html → l'image en grand + un lien retour vers la galerie

Le crawler démarre sur gallery.html, découvre les N liens, les visite un par un.
Rejouable. Usage : .venv/bin/python scripts/gen_mockhost_pages.py
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
.topbar { text-align:center; background:#10161f;
  border-bottom:1px solid #1c2530; color:#7d8590;
  font-size:.82rem; padding:8px 16px; }
.wrap { max-width:960px; margin:24px auto 60px; padding:0 20px; }
h1 { font-size:1.2rem; }
.grid { display:grid; gap:12px;
  grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); }
.thumb { display:block; text-decoration:none; color:inherit; }
.box { display:block; width:100%; aspect-ratio:1; border-radius:10px;
  background:linear-gradient(135deg,#1e3a5f,#2dd4bf); }
.thumb span { display:block; font-size:.78rem;
  color:#7d8590; margin-top:6px; }
.big { width:100%; max-width:560px; border-radius:14px;
  border:1px solid #1c2530; display:block; }
.muted { color:#7d8590; font-size:.85rem; }
</style>"""

_PAGE = """<!doctype html>
<html lang="fr"><head><meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
__STYLE__
</head><body>
<div class="topbar">connecté · <b style="color:#e6edf3">@sample_profile</b></div>
<div class="wrap">
__BODY__
</div></body></html>
"""

_GALLERY_BODY = """<h1>Médias de @sample_profile</h1>
<p class="muted">Chaque vignette est un lien vers la page du média.</p>
<div class="grid">
__THUMBS__
</div>"""

# Vignette = un simple bloc + lien (PAS d'<img>) : l'image n'existe QUE sur la
# page photo, donc le crawler doit suivre le lien pour la trouver.
_THUMB = (
    '<a class="thumb" href="photo/__I__.html">'
    '<span class="box"></span>'
    "<span>média __NN__</span></a>"
)

_PHOTO_BODY = """<p><a href="../gallery.html">← retour à la galerie</a></p>
<h1>Média __NN__</h1>
<img class="big" src="../images/img-__NN__.svg" alt="média __NN__" />
<p class="muted">Mock · aucune donnée réelle.</p>"""


def _page(title: str, body: str) -> str:
    return _PAGE.replace("__TITLE__", title).replace("__STYLE__", _STYLE).replace("__BODY__", body)


def main() -> None:
    (ROOT / "photo").mkdir(parents=True, exist_ok=True)
    thumbs = "\n".join(
        _THUMB.replace("__I__", str(i)).replace("__NN__", f"{i:02d}") for i in range(1, N + 1)
    )
    gallery = _page("@sample_profile — galerie", _GALLERY_BODY.replace("__THUMBS__", thumbs))
    (ROOT / "gallery.html").write_text(gallery, encoding="utf-8")
    for i in range(1, N + 1):
        body = _PHOTO_BODY.replace("__NN__", f"{i:02d}")
        (ROOT / "photo" / f"{i}.html").write_text(_page(f"média {i:02d}", body), encoding="utf-8")
    print(f"✅ gallery.html + {N} pages photo (photo/1..{N}.html)")


if __name__ == "__main__":
    main()
