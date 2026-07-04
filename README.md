# 🏆 Mira — RAISE Hackathon 2026 (Cockpit)

> Workspace de build, équipe de 5. Ship une démo qui **marche**. Submission **dimanche 12h00**.
> Repo : `github.com/Cimeci/Mira` · Archi & moteur → `ARCHITECTURE.md` · Workflow équipe → `CONTRIBUTING.md` · Board → `TASKS.md`

**Une grande partie du code se fait avec Claude Code** (pas obligatoire). Si tu l'utilises : ouvre-le dans ce dossier, il lit `CLAUDE.md` automatiquement et connaît d'entrée toutes les règles, le workflow git et le standard de code. Dis-lui juste ta lane (Core/Backend/UI/Infra/Démo). Les mêmes règles s'appliquent si tu codes à la main.

## ▶️ Lancer le squelette (tourne sur la stdlib, zéro install)
```bash
python3.11 -m mira.demo      # joue les 3 beats de démo (tout mocké)
# ou, environnement complet :
bash setup.sh && source .venv/bin/activate
python -m mira.demo ; pytest -q ; ruff check .
```

## 🚀 Tout lancer en local (une commande)
```bash
bash dev.sh                  # API pipeline :8000 · locator CU :8001 · face-verifier :3001
```
Ctrl+C arrête tout. Ports surchargeables via `MIRA_API_PORT` / `MIRA_WEB_PORT` /
`FACE_VERIFIER_PORT`. Le face-verifier (Node) n'est démarré que si
`services/face-verifier/node_modules` existe (`cd services/face-verifier && npm install`).
Le pipeline `Mandate → Locate → Analyze → Notify` tourne end-to-end avec des **mocks**. Chaque lane remplace le mock de son stage par le vrai, derrière les interfaces gelées de `mira/types.py`. Guardrails Mira dans `CLAUDE.md`.

## ⏱️ Timeline (4–5 juil, venue ferme 22h sam / rouvre 7h dim)

| Bloc | Objectif |
|------|----------|
| **Sam matin (dès 8h30)** | Choisir track + problem statement · lock l'idée · scaffold + 1er déploiement Vercel vide |
| **Sam aprem** | **Vertical slice end-to-end qui tourne** (le chemin de démo). Rien d'autre ne compte tant que ça ne marche pas. |
| **Sam soir (hors site)** | Élargir la démo · brancher la stack sponsor à fond · fiabiliser |
| **Dim matin** | Freeze features 10h. Polish démo · enregistrer **vidéo 1 min** · répéter pitch 3 min |
| **Dim 12h00** | **SUBMIT** (form + vidéo + repo public) |

## ✅ Checklist submission
- [ ] Repo **public** + **LICENSE MIT** (déjà en place)
- [ ] Démo live déployée (Vercel preview URL) qui tourne sans toi
- [ ] Vidéo 1 min (Loom/YT) — montre le résultat, pas le code
- [ ] Pitch 3 min prêt : problème → démo → pourquoi ça claque sur la stack sponsor
- [ ] Formulaire de soumission rempli
- [ ] README repo : quoi + comment lancer + quelle stack sponsor

## 📌 Statut projet
- **Track** : Safety, Compliance & Agentic AI
- **Idée** : Mira — agent assistif *consent-first* qui aide une victime de deepfake sexuel non consenti à en obtenir le retrait sous droit EU (RGPD/DSA/loi SREN).
- **Pipeline** : Mandate → Locate → Analyze → Notify (consent unlocks autonomy).
- **Chemin de démo (3 beats)** : (1) pas de mandat → l'agent refuse · (2) pipeline complet → notice DSA dans l'inbox · (3) flag mineur → halt + escalade, zéro stockage.
- **Surface démo** : _à trancher (Next+FastAPI SSE / tout-Python FastAPI SSE)_
- **URL démo** : _TBD_

## 🚫 Rappels qui disqualifient
NEW WORK ONLY (zéro Softcallia/code existant) · 100% OSS/MIT · pas de RAG basique / Streamlit / image analyzer / chatbot générique / CV screener / conseil médical.

→ Architecture technique (agents + computer use Gemini + infra + légal) : `ARCHITECTURE.md`
→ Détails orga + playbook skills : `CHEATSHEET.md`
