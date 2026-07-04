# Mock host — fixture de démo pour le Locator computer use (L1)

Page statique **synthétique** servie localement pour exercer le Locator réel
(`mira/locator_cu.py`) et exécuter le **go/no-go** de ce soir. Aucun contenu réel (G-10).

La page `target/index.html` contient 4 images **in-scope** (host courant + préfixe
`/target`) et 1 image **hors-scope** (`evil-mirror.example`) qui **doit être jetée** par
l'enforcement G-2 — jamais mise en queue.

## Lancer le go/no-go (nécessite deps + clé)

```bash
# 1. Deps réelles (impacte L4 — cf. requirements.txt)
pip install google-genai playwright
playwright install chromium

# 2. Clé Gemini/Vertex dans l'environnement
export GEMINI_API_KEY=...            # AI Studio
# — ou — Vertex AI :
# export GOOGLE_GENAI_USE_VERTEXAI=1 GOOGLE_CLOUD_PROJECT=... GOOGLE_CLOUD_LOCATION=us-central1

# 3. Servir le mock host (un terminal)
python -m http.server 8000 --directory mock_host

# 4. Lancer les 3 essais go/no-go contre la page cible (autre terminal)
MIRA_LOCATOR_REAL=1 python -m mira.locator_cu --url http://localhost:8000/target/
```

Le harnais imprime `=== GO ===` ou `=== NO-GO ===` selon le critère écrit en tête de
`mira/locator_cu.py` (3/3 essais < 90 s, ≥1 média in-scope, 0 hors-scope, 0 fallback).

> Les fichiers `synthetic_*.jpg` n'ont pas besoin d'exister : l'extraction lit `img.src`
> (URL absolue résolue) même si l'image 404. Ajoute de vraies vignettes si tu veux des
> screenshots plus « réels » pour la vidéo.
