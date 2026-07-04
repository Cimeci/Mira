# 🗺️ PLAN — Qui fait quoi (hackathon ~15h)

> Le but commun : **les 3 beats de démo en live** — dépôt URL + mandat → les 3 agents visibles en temps réel → gate victime → notice envoyée sur l'inbox de démo, + le chemin mineur (halt & escalade) sur un cas synthétique séparé.
>
> Les décisions moteur/infra/légal sont dans `ARCHITECTURE.md`. Ce fichier dit **qui fait quoi, dans quel ordre, et qui débloque qui**. Board de suivi : `TASKS.md`.

---

## ⚡ Décisions figées (résumé)

- **Backend tout-Python** : FastAPI + SSE dans **le même process** que l'orchestrateur (`mira/api.py`). Zéro API route Next.js métier. **Vercel = frontend only.**
- **Gemini 2.5 Computer Use = cerveau, Playwright = bras.** Local d'abord ; Browserbase / Cloud Run **après** le vertical slice (garde-fou §4.1).
- **`MIRA_CU=mock|live`** : le mock reste le défaut. `python3.11 -m mira.demo` doit rester vert **à tout moment** — c'est le filet de sécurité de la démo.
- **La couture front↔back tient dans un seul fichier : `docs/API.md`** (5 endpoints + schéma des événements SSE). `web/src/lib/api.ts` (TS) et `mira/api.py` (Python) en sont chacun un miroir.
- **Rôles ajustés** (remplace le tableau §9 d'ARCHITECTURE.md pour le hackathon) : **Com + Yue en binôme** sur orchestration + DA/frontend ; **infra Docker/Cloud Run → Ilan** (phase D uniquement).

---

## 📅 Les 4 phases

| Phase | Fenêtre | Objectif de sortie |
|---|---|---|
| **A — Setup** | H0 → H1 | Tout le monde tourne en local, contrats figés (`API.md`, schéma events) |
| **B — Vertical slice mock** | H1 → H5 | Front → API → orchestrateur → SSE → gate → notice, **tout en mock**, end-to-end |
| **C — Le vrai** | H5 → H11 | Chacun remplace SON mock derrière la même interface (CU live, embeddings, notice réelle) |
| **D — Fiabilité + livrables** | H11 → H15 | Répétitions démo, vidéo 1 min, pitch, Cloud Run **si** le temps le permet |

**La règle d'or : personne n'attend personne.** La phase B donne à chacun une interface mock qui tourne ; en phase C on remplace son propre mock sans toucher au reste.

---

## 👤 Ilan — Tech Lead : API/SSE + harnais CU + PR + infra (fin)

1. **H0-H1** — Écrire `docs/API.md` (5 endpoints + schéma SSE) → **déblocage n°1 de Com**. Clé Google AI Studio, deps (`google-genai`, `playwright`), smoke test du modèle CU.
2. **H1-H3** — `mira/api.py` + `mira/events.py` : FastAPI branché sur l'orchestrateur **mock**. Dès que le SSE crache des events mock, L3 est autonome.
3. **H3-H5** — Spike CU (`scripts/cu_spike.py`) : prouver la boucle screenshot → action → reboucle. **Figer la signature `run_cu_task` avec Anne-Sal.**
4. **H5-H9** — Le harnais `mira/cu/` : `loop.py` (boucle + watchdog + max_steps), `browser.py` (Playwright), `guardrails.py` (allowlist G-2, read-only), `trajectory.py` (recording JSON).
5. **H9-H11** — Brancher le remplissage de formulaire du Notifier sur le mockhost, derrière la gate G-7.
6. **H11-H15** — Infra : Dockerfile (Python + Playwright + Chromium), deploy Cloud Run, secrets. **Première chose à sacrifier si le CU déborde** — la démo peut tourner en local.
7. **En continu** — Relecture / merge des PR.

✅ **Done quand** : la live view streame du réel, et `run_cu_task` remplit le faux formulaire de takedown en autonomie.

## 👤 Anne-Sal — Agent de collecte (binôme CU avec Ilan)

1. **H1-H3** — Pendant le spike d'Ilan : écrire la **tâche de collecte** (prompt Gemini CU, critères de sortie : quelles URLs médias remonter, cas limites du mockhost : scroll, pagination).
2. **H3-H5** — Figer `run_cu_task` avec Ilan, tester sa tâche sur le spike.
3. **H5-H9** — Locator live sur le harnais : read-only strict, scope G-2, derrière `MIRA_CU=mock|live` (la signature `locate(mandate, out)` ne change PAS — contrat gelé).
4. **H9-H11** — Enregistrer une **trajectoire de secours** (cache anti-flaky, §2.5) + vérifier que les screenshots sont floutables pour la live view.

✅ **Done quand** : `MIRA_CU=live` fait émettre par `locate()` les vrais `MediaItem` du mockhost, et une trajectoire enregistrée est rejouable.

## 👤 nada — Analyzer + stockage + légal

1. **H1-H5** — Analyzer réel derrière la signature existante : **pré-check mineur D'ABORD** (déclenché par metadata/URL en démo, jamais par une image — G-4/G-6) → `ESCALATED` sans aucun stockage. Puis match embeddings visage + pHash + seuil deepfake.
2. **H5-H8** — Persistance du case store (Supabase, ou SQLite si plus rapide) : URLs + hash + embeddings, **jamais d'images** (G-5).
3. **H8-H11** — Template de la notice DSA art. 16 : base légale exacte, déclaration de bonne foi, ligne transparence IA (G-7/G-9) — consommé par le Notifier.

✅ **Done quand** : cas synthétique adulte → `VERIFIED` avec `ForensicRecord` complet ; cas mineur synthétique → `ESCALATED`, zéro octet stocké.

## 👥 Com + Yue — binôme orchestration + DA/frontend

> Un driver par sujet, l'autre en review, et **un livrable commun** là où les deux sujets se touchent : la **live agent view** (= l'orchestration rendue visible). Les PR du binôme se relisent en interne.

1. **H0-H1 — ensemble** : figer en parallèle la palette/typo depuis `icon.png` (`web/src/styles/tokens.css`) et le **schéma des événements** (`stage`, `step`, `action`, `screenshot_ref`…) → co-signé dans `docs/API.md` avec Ilan.
2. **H1-H5 — split driver/reviewer** :
   - **Driver orchestration** (Yue) : queues entre stages, consent gate G-1, timeouts/watchdog, purge sur révocation, émission des events vers `events.py`. **+ le mockhost en H1-H2** (galerie synthétique + faux formulaire de takedown, page statique ~1h) — priorité absolue, ça débloque Anne-Sal et Ilan.
   - **Driver DA/front** (Com) : la **live agent view d'abord** (contre une fixture SSE locale, sans attendre le back), puis dépôt/mandat (KYC : embeddings **côté client**), puis gate notice.
3. **H5-H9 — convergence** : brancher la live view sur le vrai flux d'events. Le binôme possède les deux bouts du fil → zéro ping-pong entre lanes. Puis landing + suivi, flou des screenshots, transitions compositor-friendly (vidéoprojecteur).
4. **H9-H15** — Polish, re-check J+7 simulé, robustesse (`FAILED` propre, jamais un silence), et **storytelling** : script `DEMO.md` + vidéo 1 min (DA de Com centrale).

✅ **Done quand** : la live agent view affiche en temps réel ce que l'orchestrateur fait vraiment, et les 5 écrans sont sur le preview Vercel.

---

## 🤝 Les 3 points de synchro bloquants

| Quand | Quoi | Qui |
|---|---|---|
| **≈H1** | `docs/API.md` figé (endpoints + schéma events) | Ilan écrit, Com + Yue co-signent |
| **≈H2** | Signature `run_cu_task` figée + URL du mockhost dispo | Ilan + Anne-Sal + Yue |
| **≈H5** | **Vertical slice mock démontré ensemble** | Tous |

Ensuite : synchro toutes les 2-3h (déjà actée).

## 🔗 Qui débloque qui

```
Ilan (API.md)          ──→  Com (types TS du front)
Ilan (SSE mock)        ──→  Com (live agent view)
Yue  (mockhost)        ──→  Anne-Sal + Ilan (tests CU)
Yue  (events émis)     ──→  Ilan (API) ──→ Com (live view réelle)
Ilan + Anne-Sal (run_cu_task) ──→  locator live + notifier form-fill
nada (template notice) ──→  Notifier (Ilan)
```

## ✂️ Si ça déborde, on coupe dans cet ordre

1. **Deploy Cloud Run** → la démo tourne en local, le jury regarde le résultat, pas l'hébergeur.
2. **CU live sur le chemin de démo** → on rejoue la trajectoire enregistrée (le mock/cache reste le défaut).
3. **Écrans landing/suivi** → le cœur de démo, c'est dépôt → live view → gate.
4. **Jamais coupé** : le consent gate (G-1), le chemin mineur (G-4), la gate victime (G-7), `demo.py` vert.
