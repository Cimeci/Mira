# CHEATSHEET — Playbook skills & orga (jour J)

## 🎛️ Quel skill / commande à quel moment

| Moment | Outil | Pourquoi |
|--------|-------|----------|
| **Choisir + verrouiller l'idée** (sam matin) | `/brainstorming` puis `/premortem` | Cadre l'intention avant de coder, puis tue les risques (Tigres/Éléphants) avant d'engager 15h dessus |
| **Comprendre vite le problem statement / stack sponsor** | `/deep-research` · MCP **context7** (`resolve-library-id` → `query-docs`) · agent **Explore** | Docs à jour d'une lib/API sponsor sans deviner |
| **Scaffold + déployer** | `/vercel:bootstrap` puis `/vercel:deploy` · skills `vercel:nextjs`, `vercel:shadcn` | Preview URL = démo dès la 1re heure |
| **Brancher un LLM** | skill `vercel:ai-sdk` · skill `claude-api` (model ids, streaming, tool use) | Intégration agent propre et à jour |
| **UI qui claque pour la démo** | skill `frontend-design` · agent `vercel:ai-architect` | La démo pèse 50% — le visuel vend |
| **Ça marche vraiment ?** | `/run` · `/verify` | La démo est notée en live, pas les tests |
| **Bloqué sur un bug** | `/systematic-debugging` | Évite les fixes au pif sous stress |
| **Graphes/dashboards dans la démo** | skill `dataviz` | Un seul système visuel cohérent |
| **Vidéo 1 min léchée** | skill `remotion` (si tu veux du motion) sinon Loom | Deliverable obligatoire |
| **Paralléliser du build indépendant** | `/dispatching-parallel-agents` · agents `general-purpose` / `Explore` | Toi + agents en parallèle sur des slices disjointes |
| **Capturer une décision/learning** | skill `second-brain` | Post-hackathon, sans polluer le build |

## ⚡ Boucle de build recommandée
1. `/brainstorming` → one-liner + chemin de démo en 3 étapes.
2. `/premortem` → si un Éléphant apparaît, pivote **maintenant**.
3. Scaffold Next.js + `vercel deploy` (URL vide en ligne).
4. **Vertical slice** : la 1re des 3 étapes de démo, end-to-end, déployée.
5. `/verify` → screenshot → étape suivante. Répète.
6. Dim matin : freeze, polish, vidéo, pitch.

## 📇 Facts orga (source: Second Brain `raise-hackathon-2026.md`)
- **Cerebral Valley / cv.inc** · contact **alex@cv.inc** · Discord `N26eKqmR42`.
- Venues Paris 9e : **La Maison** (2 rue des Mathurins, track Cursor) · **Neon Noir** (14 rue Le Peletier, Vultr/DeepMind/Crusoe). Présentiel = **premier arrivé premier servi**, sois là **8h30**.
- Présentiel = **exactement 5** en équipe · remote = max 5.
- Jugement R1 ~3 min pitch + Q/A → top 3/track sur scène.
- **Statut mineur (17 ans)** : point à avoir clarifié avec alex@cv.inc (âge/soirée).

## 🎯 Grille de jugement (colle-la au mur mental)
**Demo 50 · Impact 25 · Créativité 15 · Pitch 10.**
Chaque arbitrage → « est-ce que ça rend la démo live plus impressionnante et plus fiable ? » Si non, coupe.

## 🚫 Bannis (disqualifiants)
RAG basique · Streamlit · image analyzer · chatbot générique · CV screener · conseil médical. Vise **agentique / technique / infra**.
