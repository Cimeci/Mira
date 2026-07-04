# CLAUDE.md — Mira (RAISE Hackathon 2026)

Tu aides à construire **Mira** pendant un hackathon de ~15h, au sein d'une **équipe de 5**. Une grande partie du code se fait avec Claude Code (mais pas tout, et ce n'est pas obligatoire pour l'équipe). Ta mission : shipper une **démo qui marche**, garder un code **cohérent entre plusieurs contributeurs en parallèle**, et tenir un **niveau d'ingénieur senior** sans ralentir personne.

Repo : `github.com/Cimeci/Mira` · Workflow humain détaillé : `CONTRIBUTING.md` · Board : `TASKS.md`.

---

## 🟢 Au début de CHAQUE session
1. **Demande au dev quelle lane il possède** (L1 Core/Agent · L2 Backend/API · L3 UI · L4 Infra · L5 Démo). Travaille dans les dossiers de SA lane. **Ne modifie pas le code d'une autre lane sans le signaler** — c'est la cause n°1 de conflits.
2. Rappelle-toi : **`main` doit toujours être déployable**. Jamais de commit direct sur `main`. Tout passe par une branche + PR.
3. En cas de doute sur une règle : elle est ici ou dans `CONTRIBUTING.md`. Ne l'invente pas.

## 🎯 Comment on est jugé → ta fonction de priorité
**Demo 50% · Impact 25% · Créativité 15% · Pitch 10%.**
À chaque arbitrage, pose-toi : *« est-ce que ça rend la démo live plus fiable ou plus impressionnante ? »* Si non → coupe. Une feature qui ne se démontre pas en direct ne vaut rien ce week-end.

## 🚧 Le cadre (règles orga, non négociables)
- **100% open source, licence MIT** (déjà en place). Repo public.
- **NEW WORK ONLY, vérifié** : interdit de réutiliser du code préexistant. **Ne jamais importer/copier Softcallia, ProspAction, Pyralys, prospector-suite.** Tout part de zéro dans ce repo.
- **Anti-projets bannis (disqualifiants)** : RAG basique, Streamlit, image analyzer, chatbot générique, CV screener, conseil médical. → viser **technique / agentique / infra**.
- **Deliverables** : formulaire + **vidéo 1 min** + pitch R1 ~3 min.
- Le contenu de `reference/` est **inspiration seulement**, jamais réutilisé comme code (règle new-work-only).

---

## 🧠 Le standard d'ingénierie — « senior, pas bâclé »
Senior ≠ lent. Senior = **choisir délibérément ce qu'on fait bien et ce qu'on skippe**, et ne jamais shipper un truc qui casse en silence.

- **Les types sont des contrats** : TypeScript strict. Pas de `any` sans `// raison`, pas de `@ts-ignore` sans commentaire. Modélise les données avec des types précis — un mauvais type = un bug de démo en puissance.
- **Fonctions courtes, nommées, une seule responsabilité.** Un fichier = une chose. Nomme pour que le coéquipier lise une fois et comprenne.
- **Pas d'abstraction prématurée.** Deux usages avant d'extraire. Dupliquer une fois est OK ; à la troisième, on factorise.
- **Zéro échec silencieux.** Pas de `catch {}` vide. Si ça peut planter pendant la démo, ça doit gueuler en dev. Valide les entrées aux frontières (handlers API, données externes).
- **Fail fast.** Un état impossible doit crasher tôt et clairement, pas produire un résultat faux plus loin.
- **Supprime le code mort.** Pas de blocs commentés « au cas où ». Git garde l'historique.
- **Les commentaires expliquent le POURQUOI, jamais le QUOI.** Le code dit le quoi.

## ✂️ Ce qu'on skippe délibérément (c'est un hackathon)
- **Tests exhaustifs** → NON. On teste **une seule chose : le chemin de démo end-to-end**. Rien d'autre n'a besoin de couverture.
- **Edge cases hors démo** → happy path + les 2-3 inputs qu'on montrera en live, point.
- **Config spéculative** (feature flags, i18n, theming avancé, micro-optims) → non, sauf si ça sert la démo.
- Si tu hésites entre « propre » et « démontrable maintenant » → **démontrable maintenant**, puis on nettoie si le temps le permet.

## 🔁 Cohérence entre les 5 Claude (crucial)
5 sessions Claude indépendantes éditent ce repo. **La cohérence prime sur la cleverness :**
- **Grep avant d'écrire** : réutilise un composant/util existant plutôt que d'en créer un doublon.
- **Suis le pattern du fichier que tu édites** plutôt que ta préférence perso.
- **Aligne-toi** sur le nommage, la structure de dossiers et le style d'import déjà présents.
- Nouvelle dépendance ou nouveau pattern structurant → **signale-le** (ça impacte les 4 autres).

---

## 🌿 Git & collaboration (détail complet dans `CONTRIBUTING.md`)
```bash
git checkout main && git pull              # partir d'un main à jour
git checkout -b l3/ma-feature              # branche = <lane>/<slug>, courte durée de vie
# ... code ...
pnpm check                                 # typecheck + lint + format — DOIT être vert
git add -A && git commit -m "feat(ui): ma feature"
git push -u origin l3/ma-feature
gh pr create --fill                        # PR → 1 relecture rapide → merge
```
- **Branches courtes**, mergées en 1-2h. `git pull --rebase origin main` souvent.
- **Commits** : `feat|fix|chore|refactor(scope): message`. Petits et fréquents.
- **`main` cassé = tout le monde s'arrête**, L4 (Infra) répare en priorité.
- **Jamais de secret commité** → `.env.local` (gitignored), template dans `.env.example`.

## ✅ Vérifie AVANT de dire que c'est fait
La démo est notée en live. « Ça devrait marcher » ≠ « ça marche ».
- **Exécute réellement le flux** (`pnpm dev`, ouvre la route, clique le bouton) et **observe le résultat** avant de conclure.
- Surface déployée modifiée → vérifie le **preview Vercel**, pas seulement localhost.
- Avant de push : `pnpm check` vert. Non négociable.

## 🛠️ Stack & commandes
- **Cœur : Python 3.11 + asyncio** (imposé par la spec Mira). Package `mira/` : 4 stages (mandate/locator/analyzer/notifier) + `orchestrator` (consent gate) + `types` (contrats gelés). Le pipeline tourne end-to-end sur des **mocks** ; chaque lane remplace le mock de son stage par le vrai, derrière la même interface.
- **Surface démo (front)** : à trancher (Next.js+FastAPI SSE, ou tout-Python FastAPI+SSE). Pas de Streamlit (banni).
- **LLM** : rédaction de notice / instructions locator. Track Google → **Gemini/Gemma** ; sinon **Claude** (`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5-20251001`).
- Commandes : `bash setup.sh` (venv + deps) · `python -m mira.demo` (les 3 beats, mocks) · `pytest -q` · `ruff check .`. Le squelette tourne **sans rien installer** (stdlib) : `python3.11 -m mira.demo`.
- Toolchain : python 3.11 (Homebrew), node 24, pnpm 9, vercel CLI, gh, git.

## 🔒 Guardrails Mira (issus de la spec §13 — non négociables)
- **G-1** aucun stage ne tourne sans `Mandate.active` (vérifié dans l'orchestrateur, une fois).
- **G-2** le Locator reste strictement dans `scope_urls` (pas de web ouvert).
- **G-6** pré-check mineur AVANT tout stockage ; mineur suspecté → **halt + escalade, jamais de download/hash/store**.
- **G-5** hash perceptuel préféré aux octets bruts ; chiffrer ce qui est retenu.
- **G-7** gate de confirmation victime avant tout envoi externe.
- **G-9** la notice cite la base légale exacte, **n'invente jamais de pénalité**.
- **G-12** la démo cible un mock host + inbox de démo uniquement — jamais de vrai contenu/plateforme.
- En démo, le flag mineur se déclenche par **metadata/URL**, jamais par une image de mineur.

## 📂 Fichiers du repo
`README.md` cockpit · `ARCHITECTURE.md` moteur agentique (computer use Gemini + workflow des agents + infra Cloud Run/Browserbase + frontend/backend/branding + cadre légal) · `CONTRIBUTING.md` workflow · `TASKS.md` board · `CHEATSHEET.md` playbook skills · `mira/` le code · `tests/` smoke tests · `reference/` inspiration (jamais réutilisée comme code).
