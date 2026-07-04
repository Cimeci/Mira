# CLAUDE.md — RAISE Summit Hackathon 2026 (workspace de build)

Ce dossier est un **workspace de hackathon**. On ship vite, on démontre, on gagne. Optimise pour **une démo qui MARCHE**, pas pour la propreté du code.

## Le cadre (non négociable — règles de l'orga)
- **Event** : RAISE Summit Hackathon, orga **Cerebral Valley (cv.inc)**, Paris 9e, **4–5 juillet 2026**. Submission **dimanche 12h00**.
- **100% open source** : tout le code sous licence **MIT** (LICENSE déjà en place). Repo public.
- **NEW WORK ONLY, vérifié** : interdit de réutiliser du code préexistant. **NE PAS toucher / importer / copier Softcallia, ProspAction, Pyralys, prospector-suite.** Tout part de zéro dans CE dossier.
- **Anti-projets bannis** (disqualifiants) : RAG basique, app Streamlit, image analyzer, chatbot générique, CV screener, conseil médical. → viser **technique / agentique / infra**.
- **Deliverables** : formulaire de soumission + **vidéo 1 min** (Loom/YT) + **pitch R1 ~3 min + Q/A**.

## Comment on est jugé (drive TOUTES les priorités)
**Demo 50% · Impact 25% · Créativité 15% · Pitch 10%.**
→ Corollaire : à tout arbitrage, **choisir ce qui rend la démo live plus impressionnante et plus fiable**. Une feature qui ne se démontre pas en direct ne vaut rien ce week-end.

## Tracks (choisir une fois les problem statements sortis)
Cursor · Google DeepMind · Vultr · Crusoe. Pattern gagnant 2025 : **outil agentique/technique B2B déployé à fond sur la stack du sponsor**. Edge de Côme = full-stack solo qui ship → rôle **intégrateur qui fait tourner la démo**.

## Stack par défaut (change si le track l'impose)
- **Front / démo** : Next.js (App Router) + TypeScript + Tailwind, déploiement **Vercel** (preview URL = démo instantanée).
- **Agent / backend** : Node/TS d'abord (vitesse) ; Python3 si lib ML l'exige.
- **LLM** : track Google → **Gemini / Gemma** (AI Studio). Sinon Claude (`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`) via le SDK Anthropic. Toujours viser les modèles les plus récents.
- Toolchain dispo : node 24, pnpm 9, vercel CLI, gh, git, python3.9.

## Règles de travail (mode hackathon)
1. **Vertical slice d'abord** : le chemin de démo end-to-end qui marche > la feature complète. Fais-le tourner, screenshot, puis élargis.
2. **Déploie tôt et souvent** sur Vercel — jamais de "ça marche en local" la veille de la deadline.
3. **Pas d'over-engineering** : pas de tests exhaustifs, pas d'abstractions. Le code jetable est OK ici.
4. **Vérifie en exécutant** (`/run`, `/verify`) avant de dire que ça marche — la démo est notée en live.
5. Commits fréquents et petits (repo public OSS). Messages courts.

## Où est quoi
- `README.md` — cockpit du jour (timeline, checklist, statut projet).
- `CHEATSHEET.md` — playbook skills/agents + facts orga + do/don't.
- `reference/` — matériaux RAISE antérieurs en lecture seule (premortem, decks). **Ne pas réutiliser comme code** (règle new-work-only), juste comme inspiration.
- `scratch/` — brouillons, tests jetables.
