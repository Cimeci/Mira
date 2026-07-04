# CONTRIBUTING — Workflow équipe (5 personnes, mode hackathon)

Objectif : **5 personnes qui ship en parallèle sans se marcher dessus, avec un `main` qui tourne toujours**. Qualité = ça ne casse pas la démo. Pas de bureaucratie.

## 1. Règle d'or
**`main` est toujours déployable.** On ne push jamais du code cassé sur `main`. Tout passe par une branche + PR courte (même 10 min de review suffit). Vercel déploie `main` en auto → si `main` casse, la démo casse.

## 2. Découpage en 5 lanes (zéro collision)
Chacun **possède** un dossier/surface. On ne touche pas la lane d'un autre sans le prévenir (→ évite 90% des merge conflicts).

| Lane | Owner | Périmètre | Dossier |
|------|-------|-----------|---------|
| **L1 — Core / Agent** | _TBD_ | Le moteur agentique/technique = le "wow" | `src/core/`, `src/agent/` |
| **L2 — Backend / API / Data** | _TBD_ | Endpoints, DB, intégration stack sponsor | `src/app/api/`, `src/lib/` |
| **L3 — Frontend / UI** | _TBD_ | La surface de démo | `src/app/(ui)/`, `src/components/` |
| **L4 — Infra / Deploy / DX** | _TBD_ | Vercel, CI, env, garde `main` vert, débloque les autres | `.github/`, config, `setup.sh` |
| **L5 — Intégration / Démo / Pitch** | _TBD_ | Colle le tout, écrit le script de démo, vidéo, pitch. Owner du "est-ce que ça tourne end-to-end" | `demo/`, `DEMO.md` |

Renseignez les owners samedi matin dans `TASKS.md`.

## 3. Flow git (trunk-based, branches courtes)
```bash
git checkout main && git pull            # toujours partir d'un main à jour
git checkout -b l3/hero-section          # branche = <lane>/<slug>, courte durée de vie
# ... code ...
pnpm check                               # typecheck + lint + format AVANT de push (voir §4)
git add -A && git commit -m "feat(ui): hero section"
git push -u origin l3/hero-section
gh pr create --fill                      # PR → 1 relecture rapide → merge
```
- **Branches courtes** : merge dans les 1-2h max. Une branche qui vit une journée = enfer de conflits.
- **Rebase sur main souvent** (`git pull --rebase origin main`) pour rester à jour.
- **Petits commits** avec préfixe : `feat() fix() chore() refactor()` + scope de lane.
- **Jamais de secrets commités** → voir `.env.example`.

## 4. Gates de qualité (automatisés, rapides)
- **Pre-commit** (husky + lint-staged) : formate + lint les fichiers stagés automatiquement. Invisible, rapide.
- **`pnpm check`** avant push : `tsc --noEmit && eslint . && prettier --check`.
- **CI GitHub Actions** (`.github/workflows/ci.yml`) : rejoue typecheck + lint + build sur chaque PR. Une PR rouge ne merge pas.
- **TypeScript strict** : pas de `any` sauvage, pas de `@ts-ignore` sans commentaire.

→ Activer tout ça d'un coup après avoir choisi le track : **`bash setup.sh`** (scaffold Next.js + tooling qualité + husky).

## 5. Standard de code (hackathon = pragmatique mais propre)
- **Nommage explicite**, fonctions courtes, un fichier = une responsabilité.
- **Pas d'over-engineering** : pas d'abstraction spéculative, pas de tests exhaustifs. On teste **le chemin de démo**, point.
- **Code jetable OK** dans `scratch/` — mais ce qui va sur `main` est lisible par les 4 autres.
- **Commentaire seulement quand le "pourquoi" n'est pas évident.**
- Le review PR vérifie une chose : **est-ce que ça marche et est-ce que ça ne casse pas la démo des autres ?**

## 6. Comms
- Une décision qui impacte une autre lane → dis-le à voix haute / Discord équipe **avant** de coder.
- `main` cassé = **priorité absolue de L4** (Infra) de le réparer. Personne ne build sur un main rouge.
