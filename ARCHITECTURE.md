# 🧠 ARCHITECTURE — Mira : computer use, agents, infra, produit & cadre légal

> Ce fichier fige **ce que l'équipe a décidé** sur le moteur de Mira : comment on se sert de _computer use_, comment les agents s'enchaînent pour aller sur le site d'une URL et **remplir les formulaires / envoyer les mails de takedown**, dans quelle **infra** (agents dans des Docker isolés), avec quelles **surfaces produit** (frontend, backend, branding), et où passe la ligne légale (dépôt d'URL + accord de la victime).
>
> Sources : `meeting_note#1_Mira_roadmap.md` (réunion #1) + le spec EU (`project-mira-eu-spec.md`). En cas de conflit, **ce fichier tranche pour le hackathon** ; le spec reste la référence légale détaillée.
>
> ⚠️ **Pas un avis juridique.** Toute référence légale (RGPD, DSA, loi SREN…) est indicative et doit être revérifiée sur Légifrance / EUR-Lex avant tout déploiement réel. Aucune donnée de vraie victime ne transite par la démo.

---

## 0. En une phrase

Mira est un **agent de takedown consent-first pour les images non consenties (NCII / deepfakes sexuels)** : la victime dépose une URL + un mandat signé, et une chaîne d'agents va **collecter → vérifier → notifier** à sa place, sans qu'elle ait à scroller le contenu ni rédiger une seule ligne juridique.

Le principe central de la réunion : **l'IA n'a pas de sentiments, elle fait le sale boulot à la place de la victime.** Être victime _et_ devoir gérer soi-même les démarches = double traumatisme. On supprime ça.

---

## 1. Deux périmètres, ne pas les confondre

| | **V1 — Chemin de démo (réactif)** | **V2 — Goal max (proactif, incertain)** |
|---|---|---|
| **Déclencheur** | La victime **dépose une URL** (reçue d'un ami, trouvée par hasard) | La victime **scanne son visage**, on part crawler pour elle |
| **Scope** | Les surfaces que la victime autorise, point | Une **allowlist** de sites connus pour les deepfakes |
| **Ce qu'on construit ce week-end** | ✅ **Oui** — c'est la démo notée | 🟡 Roadmap / vision long terme (les ~15% du jury) |
| **Coût computer use** | Borné, démontrable en live | Lent + cher — **la réunion a acté de NE PAS scanner l'open web en V1** |
| **Poids légal** | Léger : la victime pointe elle-même le contenu | Lourd : traitement proactif de données sensibles → consentement explicite + DPIA **obligatoires** |

> **Décision d'équipe.** On **ship V1**, on **pitche V2**. V2 n'est défendable que sur une base précise (§8) : c'est **le propre visage de la victime**, avec **son consentement explicite**, sur un **périmètre restreint** — jamais un crawl de l'open web sur des inconnus. Sans ça, V2 est illégal, pas juste ambitieux.

---

## 2. Computer use — la recherche & le choix

### 2.1 Le problème que ça résout

Chaque plateforme a son propre mécanisme de signalement : formulaire web maison, portail DSA, `abuse@`, captcha, scroll infini, connexion requise. Pas d'API unifiée. **Computer use** = un agent qui _voit l'écran et agit comme un humain_ (bouge le curseur, clique, tape, scrolle), donc il absorbe cette hétérogénéité sans qu'on code un connecteur par site.

Contrepartie : **c'est lent par nature** — boucle `screenshot → analyse → action suivante`, quelques secondes par étape. On l'assume et on l'isole.

### 2.2 On est sur le track Google → **Gemini 2.5 Computer Use**

**Décision figée : le moteur computer use de Mira est Gemini 2.5 Computer Use** (`gemini-2.5-computer-use`, dispo via **Google AI Studio** et **Vertex AI**). C'est le choix imposé par le track sponsor, et c'est un **atout de pitch** : Google annonce qu'il bat Claude Sonnet et les agents OpenAI sur les benchmarks de contrôle d'interface web/mobile, **avec moins de latence** — exactement notre goulot (computer use est lent par nature).

Comment ça marche — un **outil `computer_use`** piloté en boucle :

```
  requête + screenshot + historique d'actions
                    │
                    ▼
        Gemini 2.5 Computer Use
                    │  → action recommandée (clic / frappe / scroll)
                    │  → peut DEMANDER CONFIRMATION sur une action à risque
                    ▼
        on exécute l'action (via Playwright / Browserbase)
                    │
                    ▼
        nouveau screenshot renvoyé au modèle → on reboucle
                    │
            jusqu'à tâche finie / halt (erreur ou décision de sûreté)
```

Il sait nativement **remplir et soumettre des formulaires**, manipuler dropdowns/filtres, et opérer **derrière un login** — c'est précisément le geste de takedown qu'on automatise.

### 2.3 Le reste de la stack autour de Gemini CU

| Brique | Rôle | Pourquoi |
|---|---|---|
| **Gemini 2.5 Computer Use** | **Cerveau** de l'agent : décide l'action UI à partir du screenshot | Track Google, meilleurs benchmarks contrôle UI, latence basse, form-filling natif |
| **Playwright** (Chromium) | **Bras** : exécute réellement clics/frappes/scroll, chemin de démo figé | Substrat d'exécution recommandé par Google pour Gemini CU ; déterministe et stable au vidéoprojecteur |
| **Browserbase** (sandbox) | Environnement navigateur isolé prêt à l'emploi | Démarrage rapide, isolation, alternative si on ne gère pas l'infra nous-mêmes |
| **Gemini / Gemma** (2.5) | Rédaction de la notice DSA, instructions au locator, raisonnement | Même track Google ; Gemma pour les tâches légères/locales |

### 2.4 Ce qu'on décide

- **Gemini 2.5 Computer Use = cerveau ; Playwright = bras.** Le modèle décide l'action, Playwright l'exécute. Pour le **chemin de démo critique**, on peut figer la trajectoire en Playwright pur (fiabilité live) et laisser Gemini CU gérer l'adaptatif (captcha, UI inconnue) sur les cas « wow ».
- **Deux fronts en parallèle** (acté en réunion) : **scraping browser** + **simulateur mobile** — certains sites/formulaires n'existent qu'en app.
- **Tout tourne dans des containers Docker** (ou sandbox Browserbase), **jamais sur le device de la victime**. Isolation, privilèges minimaux, accès réseau restreint. Un agent qui pilote un navigateur est une surface à risque — on le sandboxe.
- **Human-in-the-loop au bord** : Gemini CU sait déjà **demander confirmation sur une action à risque** — on branche ça sur notre gate de victime (§6). Rédaction et résolution autonomes, mais **la victime valide avant tout envoi externe**.

### 2.5 Fiabilité — ce qu'on met en place

Boucle d'action robuste (galère connue des agents navigateur) :
- **Context caching** Gemini + images bien dimensionnées + pruning des vieux screenshots (le budget tokens explose sur les longues sessions).
- **Timeouts + backoff** sur toute I/O, **watchdog** anti-stall (une coroutine qui tue les boucles bloquées).
- **Trajectory recording** : on log chaque action (screenshot + décision) → rejouable, débuggable, et ça alimente la preuve d'audit.
- Anti-bot (captcha, Cloudflare) = risque n°1 connu → on s'appuie sur la capacité de Gemini CU à agir comme un humain, et on **cache la réponse pour la démo** (pas de dépendance live fragile au vidéoprojecteur).

---

## 3. Architecture workflow — les agents

Pipeline **Mandat → Localise → Vérifie → Notifie**. Le consentement débloque l'autonomie ; sans mandat actif, **aucun agent ne tourne** (garde-fou dur au niveau de l'orchestrateur, pas laissé à chaque agent).

```
+------------------------------------------------------------------+
|                    ORCHESTRATEUR (async runtime)                 |
|        Consent gate : refuse de lancer si Mandate.active == False |
+--------+------------------+------------------+--------------------+
         |                  |                  |
         v                  v                  v
+----------------+  +----------------+  +--------------------------+
| AGENT COLLECTE |  | AGENT VERIF    |  | AGENT LÉGAL / NOTIFIER   |
| (computer use) |  | (embeddings)   |  |                          |
|                |  |                |  | Résout l'hébergeur (RDAP)|
| Va sur les URLs|  | Compare le     |  | Rédige la notice DSA a.16|
| in-scope,      |  | visage victime |  | Déclar. bonne foi + IA   |
| simule humain, |  | aux images     |  | GATE confirmation victime|
| bypass captcha,|  | collectées     |  | Remplit le formulaire /  |
| scroll infini  |  | Pré-check      |  | envoie le mail (takedown)|
| Read-only      |  | mineur (STOP)  |  |                          |
+-------+--------+  +-------+--------+  +------------+-------------+
        |                   |                        |
        +-------------------+------------------------+
                            v
              +-------------------------------+
              |   CASE STORE chiffré          |
              |   URLs + hash + embeddings    |
              |   (jamais les images brutes)  |
              |   access-logged, rétention    |
              +-------------------------------+
```

### 3.1 Les trois couches (réunion) mappées sur les étapes (spec)

| # | Agent (réunion) | Étape (spec) | Rôle concret |
|---|---|---|---|
| **0** | — (gate) | **Mandate** | Enregistre identité + consentement + scope. Débloque le reste. Révocable → purge. |
| **1** | **Agent de collecte** (computer use) | **Locator** | Visite **uniquement les URLs du scope**, simule les actions humaines (scroll infini, bypass captcha), **read-only** (pas de login, pas de submit, ne suit pas les liens hors scope). Ne juge pas le contenu. Sort des URLs média candidates. |
| **2** | **Agent de vérification** | **Analyzer** | **Pré-check mineur d'abord** (→ STOP + escalade, §7). Puis compare les **embeddings faciaux** de la victime aux images collectées (gère les faux positifs) + score deepfake. Capture une **preuve minimale** (hash perceptuel + URL + timestamp), pas les octets bruts. |
| **3** | **Agent légal** | **Notifier** | Identifie plateforme + pays d'hébergement + pays de la victime → **remplit la plainte en ligne / envoie DMCA·DSA / contacte l'hébergeur**. En France, **signature de la victime requise** sur le mandat. Gate de confirmation avant tout envoi. |

### 3.2 Machine à états

```
 MANDATED --> LOCATED --> VERIFIED --> CONFIRMED --> NOTIFIED --> [RE-CHECK J+7]
 consent      URL in-     hash +       victime      notice DSA    vérifie le
 + scope      scope       embeddings   approuve     envoyée       retrait effectif
    |            match                                   
    | revoked                 | mineur suspecté          | score < seuil
    v                         v                          v
 REVOKED                  ESCALATED                   REJECTED
 purge data               autorités + halt            jeté (0 stockage)
```

- **Communication inter-agents** : `asyncio.Queue` entre chaque étape (Locator → Analyzer → Notifier). Chaque agent est un consommateur/producteur async indépendant → testable isolément avec des APIs mockées.
- **Deux cas produit couverts** (réunion) : **ciblé** (streamers/célébrités, mêmes images spammées sur N sites) et **non-ciblé** (ressemblance issue d'un entraînement de modèle). Même pipeline, l'Analyzer gère la nuance.
- **Re-check automatique J+7** après le takedown : un agent repasse sur l'URL pour vérifier que le contenu a bien disparu. C'est ça qui rend le produit crédible (« Mira ne se contente pas d'envoyer, il vérifie »).

---

## 4. Infra & runtime — le cerveau dans un Docker contrôlé

> Le computer use pilote un vrai navigateur qui visite des sites potentiellement hostiles : c'est **lent** et c'est une **surface à risque**. On l'isole. Le **cerveau** (Gemini CU) raisonne ; le **corps** (Chromium piloté par Playwright) agit dans un container jetable, jamais sur le device de la victime ni sur l'host.

### 4.1 Topologie de déploiement (le piège Vercel à connaître)

**Vercel est serverless → timeouts courts, pas de navigateur long-running. Le computer use n'y tourne PAS.** Vercel héberge le **frontend + l'API légère** ; l'**orchestrateur + les workers** tournent en **containers sur Cloud Run** (même cloud que Vertex AI/Gemini → clé, réseau, secrets alignés, zéro serveur à administrer), avec le **navigateur isolé chez Browserbase**. Le backend fait le **pont** entre les deux. Choix assumé : **du managé, aucune VM montée à la main** — plus simple, plus propre pour 15h.

```
        VICTIME (navigateur)
              │  HTTPS
              ▼
   ┌────────────────────────────┐
   │  FRONTEND + API  (Vercel)  │   ← serverless, léger — PAS de computer use ici
   │  Next.js App Router        │
   │  · dépôt URL + mandat      │
   │  · stream état des agents  │
   │  · preview notice + gate   │
   └─────────────┬──────────────┘
                 │  job / webhook / SSE
                 ▼
   ┌────────────────────────────┐
   │  ORCHESTRATEUR + WORKERS   │   ← Cloud Run (containers, hors Vercel)
   │  (async runtime, consent gate)
   │   ┌──────────┐ ┌──────────┐ │
   │   │ browser  │ │ mobile   │ │   ← sandbox éphémère par cas (Browserbase en démo · propre container en prod)
   │   │ +Chromium│ │ simu     │ │      Gemini CU = cerveau (API Vertex AI)
   │   │ Playwright│ │          │ │      Playwright = bras (dans le container)
   │   └──────────┘ └──────────┘ │
   └─────────────┬──────────────┘
                 ▼
     CASE STORE chiffré (Postgres/Supabase)
     URLs + hash + embeddings — jamais les images
```

**Où ça tourne + qui possède quoi** (le split app / plateforme, pour éviter le seam-of-death sur le chemin critique) :

| Brique | Où | Owner |
|---|---|---|
| Frontend + API L2 (relais) | **Vercel** | Tech Lead (L2) |
| Service Cloud Run (deploy, secrets, réseau, egress) | **Cloud Run** | **L4 Infra** |
| Image du container + contrat de job + code CU dedans | **Cloud Run** | **Tech Lead** |
| Sandbox navigateur isolée | **Browserbase** (démo) → **propre container** (prod) | L4 provisionne, Tech Lead consomme |

> Règle : le Tech Lead ne **possède** pas la plateforme, mais doit pouvoir **déployer dessus sans attendre** (le worker CU est le chemin critique). `gcloud run deploy` en dépannage = OK, mais on l'annonce à L4 (on ne touche pas au lane d'un autre en silence).

**🎯 Décision hackathon — Browserbase en démo, propre container en prod.** Règle maison : *démontrable maintenant > propre plus tard*.

- **Ce week-end : navigateur chez Browserbase.** La démo tourne sur du **mock** (contenu synthétique, host mock, boîte mail de démo — cf §10) → l'argument « le contenu sensible passe chez un tiers » **ne s'applique pas**, et Browserbase supprime le time-sink n°1 : **Chromium-dans-Docker** (deps, flags de sandbox, OOM). Le **full vibe code accélère le *code*** (boucle agent, glue API, front), **pas** le debug d'infra — donc on managé là où ça fait mal.
- **Le propre container reste l'argument prod/roadmap** : *« en démo, Browserbase sur du synthétique ; en prod, le navigateur tourne dans **notre** container isolé pour que le contenu sensible ne touche jamais un tiers. »* Renforce le pitch (data sovereignty / RGPD) à **coût démo zéro** — l'option A n'est pas jetée, elle vaut des points en vision (~15 %).
- **Garde-fou** : on ne yak-shave **pas** le deploy Cloud Run **avant** que le vertical slice marche. Pour la démo live, l'orchestrateur peut tourner **en local** (le jury regarde le résultat, pas l'hébergeur). Cloud Run = la story propre du pitch + le « ça tourne sans toi » de la submission → à brancher **après** que l'end-to-end fonctionne.

### 4.2 Ce que le container garantit

| Contrainte | Pourquoi |
|---|---|
| **1 sandbox éphémère par cas** | Isolation totale entre victimes ; teardown + purge à la fin du cas ou à la révocation du mandat |
| **Privilèges minimaux, FS éphémère** | Un site hostile qui exploite le navigateur ne touche ni l'host ni les autres cas |
| **Egress réseau restreint (allowlist)** | Le worker ne parle qu'aux URLs du scope (+ APIs Gemini/store) — pas de crawl sauvage (renforce G-2) |
| **Cerveau ≠ corps** | Gemini CU raisonne via l'API Google ; seul Chromium+Playwright vit dans le container → on peut tuer/rejouer un container sans perdre la logique |
| **Deux runtimes en parallèle** (réunion) | Un container **scraping browser** + un container **simulateur mobile** — certains formulaires n'existent qu'en app |

### 4.3 Robustesse d'exécution

- **Orchestrateur** : lève le consent gate, spawn le container avec le `scope_urls` injecté, relaie l'état au backend, tue + purge à la fin.
- **Watchdog + timeouts + backoff** sur chaque job (cf §2.5) → un container bloqué est tué, pas laissé pendre.
- **Trajectory recording** persistée hors du container éphémère → rejouable, débuggable, et alimente la preuve d'audit.
- **Lane owner** : infra Cloud Run + orchestration = **L4** (cf §9) ; le Tech Lead possède l'image du container + le contrat de job.

---

## 5. Les surfaces produit — Frontend, Backend, Branding

> Le moteur agentique est le « wow », mais le jury note la **démo live**. Il faut une UI **intentionnelle** (règle maison : pas de template Tailwind par défaut) et un backend qui **relie le workflow au frontend** proprement.

### 5.1 Branding (on a déjà l'icône)

- **`icon.png`** (racine) = **graine visuelle** de Mira → à décliner en **favicon + app icon + logo header**.
- **Ton** : protecteur, digne, sérieux — **jamais victimisant ni clinique/anxiogène**. « Mira » évoque *regarder / miroir* : on prend en charge le regard à la place de la victime.
- **Avant de coder l'UI** (règle maison design-quality) : figer **palette + typographie** à partir de l'icône. Direction assumée (éditorial sobre + une couleur d'accent), pas « clean minimal » par défaut.
- **Deliverable démo** (réunion) : 1 image de présentation, **3 éléments max** + l'icône déclinée.

### 5.2 Frontend — L3 (la surface de démo)

Les écrans du chemin de démo, dans l'ordre :

1. **Landing** — la promesse : *« tu n'as pas à gérer ça toi-même »*.
2. **Dépôt** — coller l'URL + **KYC** (scan visage → **embeddings générés CÔTÉ CLIENT**, l'image ne part jamais) + **signature du mandat**.
3. **Live agent view — LE wow** : on **regarde les 3 agents bosser en temps réel** (Collecte → Vérif → Légal), chaque état qui s'allume, screenshots **floutés** du scraping, match facial (**visage only**). ⚠️ La lenteur du computer use devient un **spectacle** au lieu d'une attente morte.
4. **Preview + gate** — la notice DSA rédigée s'affiche, la victime **relit et approuve** (elle garde le contrôle, ne rédige rien).
5. **Suivi** — statut *envoyé* + **re-check J+7**.

Contraintes maison : animations **compositor-friendly** (`transform`/`opacity`, jamais `width`/`top`) — une transition qui rame se voit au vidéoprojecteur. États `hover`/`focus`/`active` soignés, hiérarchie par le contraste d'échelle.

### 5.3 Backend — L2 (le pont workflow ↔ frontend)

API routes Next.js (sur Vercel) = la colle. Responsabilités :

- **Créer** un cas + mandat en validant les entrées aux frontières (handler = frontière, on ne fait pas confiance à l'input).
- **Déclencher** l'orchestrateur (job sur le worker Docker de §4).
- **Relayer** l'état des agents au frontend en temps réel (**SSE / polling**) — c'est ce qui alimente la *live agent view*.
- **Servir** le brouillon de notice, **encaisser** l'approbation (la gate de §6).
- **Persister** URLs + hash + embeddings (Postgres/Supabase) — **jamais les images**.
- **Ce qu'il NE fait PAS** : le computer use lui-même (timeouts serverless) → il **dispatche et relaie**, il ne pilote pas le navigateur.

**Contrat de données** = les objets de §3/§8 (`Mandate`, `ForensicRecord`, statut). **Une seule source de vérité** pour la machine à états (`MANDATED → … → NOTIFIED`) partagée front / back / agents — c'est ce qui évite que les 5 sessions divergent.

---

## 6. Le flux principal V1 (ce que le jury voit)

```
1. La victime arrive sur Mira, colle une URL + signe le mandat (KYC : photo de face)
        │  (embeddings générés CÔTÉ CLIENT — l'image ne quitte pas son device)
        ▼
2. Agent COLLECTE (computer use, Docker) va sur l'URL, récupère les médias in-scope
        ▼
3. Agent VÉRIF : pré-check mineur → match embeddings visage → score deepfake
        ▼
4. Agent LÉGAL : résout l'hébergeur, rédige la notice DSA art.16 (+ déclaration bonne foi + ligne transparence IA)
        ▼
5. ⛔ GATE : la victime relit et APPROUVE la notice (elle garde le contrôle, ne rédige rien)
        ▼
6. Agent LÉGAL remplit le formulaire de signalement / envoie le mail à l'hébergeur
        ▼
7. J+7 : re-check automatique → contenu retiré ? sinon relance / escalade
```

**Ce que la victime fait** : coller une URL, signer, cliquer « approuver ». **Ce qu'elle ne fait jamais** : scroller le contenu, chercher l'hébergeur, rédiger du juridique, répéter pour chaque site.

---

## 7. Sécurité mineurs — non négociable (override tout)

Si le pré-check d'âge de l'Analyzer suggère une personne **mineure**, le contenu est un **potentiel CSAM**. Mira **NE** télécharge pas, **NE** hash pas, **NE** stocke pas, **NE** traite pas. Il **halte** (statut `ESCALATED`), **réfère** à l'autorité compétente (en France : **PHAROS**) et remonte à un opérateur humain. Détection + signalement, **jamais** manipulation — stocker ou transmettre du CSAM, même « comme preuve », est un délit grave.

---

## 8. Aspect légal — dépôt d'URL & accord de la victime

> Le cœur juridique de Mira. **Sans mandat valide, l'agent ne fait rien.** Le consentement n'est pas une politesse : sous le RGPD, c'est **ce qui rend le traitement de l'image licite tout court**.

### 8.1 Pourquoi le dépôt d'URL + accord est la clé de voûte

| Question | Réponse Mira |
|---|---|
| **Base légale du traitement ?** | Consentement explicite de la victime (RGPD Art. 6(1)(a) + Art. 9(2)(a), donnée sensible) et/ou constatation de droits en justice (Art. 9(2)(f)), **borné au scope du mandat**. |
| **Objet du délit visé** | Diffusion de deepfake non consenti — Code pénal **art. 226-8-1** (loi SREN n° 2024-449). Pour le contenu sexuel, le fait que le montage soit « évidemment faux » **n'exonère pas**. |
| **Mécanisme de retrait** | **DSA art. 16** : tout hébergeur doit offrir un mécanisme notice-and-action. Une notice conforme crée une présomption de connaissance → l'hébergeur doit agir « dans les meilleurs délais ». |
| **Signature** | En **France**, la plainte en ligne exige la **signature de la victime**. D'où le mandat signé au KYC. |
| **Fausse notice** | La **LCEN** punit une notification sciemment fausse (1 an / 15 000 €) → **chaque notice porte une déclaration de bonne foi et d'exactitude**. |
| **Transparence IA** | L'**AI Act** impose de dire que la notice est produite par un système IA assistif agissant sur mandat. Ligne obligatoire dans chaque envoi. |

### 8.2 L'objet `Mandate` (le contrat)

```
Mandate {
  case_id          : identifiant opaque, zéro PII dedans
  requester_role   : "victim" | "legal_rep" | "authorized_ngo"
  consent_ts_utc   : horodatage du consentement
  scope_urls       : les surfaces autorisées, UNIQUEMENT
  consent_artifact : preuve de consentement chiffrée (mandat signé)
  active           : false dès révocation → purge du dossier
}
```

### 8.3 Minimisation des données (anti re-victimisation)

- **On stocke les URLs + hash + embeddings, JAMAIS les images.** Les embeddings sont générés **côté client** → l'image ne quitte pas le device de la victime. En cas de fuite de la base Mira : **aucune image sensible exposée**.
- Octets bruts seulement si strictement nécessaire pour une action en justice → **chiffrés au repos, access-loggés, rétention limitée**.
- **Révocation = purge complète** du dossier (droit à l'effacement).

### 8.4 Le cas V2 (goal max) — la ligne rouge à tenir

Le scan-visage-puis-crawl est **légalement défendable seulement si** :
1. C'est **le propre visage de la victime** (pas un tiers).
2. **Consentement explicite** et éclairé, spécifiquement pour la recherche proactive (Art. 9(2)(a)).
3. Périmètre = **allowlist restreinte** de sites connus, **pas l'open web**.
4. **DPIA** (Art. 35) réalisée avant tout traitement réel.

> Sans ces quatre conditions, V2 n'est pas « ambitieux », il est **illicite**. C'est exactement pour ça qu'on le garde en roadmap et qu'on ne le démontre pas sur des données réelles.

---

## 9. Répartition des rôles → lanes du repo

| Personne | Rôle | Lane |
|---|---|---|
| **Ilan** | **Tech Lead** : backend (relais) + pont front↔workflow + **Google Computer Use** (archi / R&D / intégration en code) + résolution des PR | L2 + L5 |
| **Anne-Sal** | **Computer Use** — implémentation de l'agent de collecte (binôme CU avec Ilan) | L1 |
| **nada** | Agent de **vérification** (comparaison d'images / embeddings) + **stockage** + **aspects légaux** | L1 / L2 |
| **Yue** | **Orchestration** de l'agentic flow + **infra Cloud Run / Docker** | L4 |
| **Com** | **Direction artistique / storytelling** + **frontend UI** | L3 |

Synchro équipe : **toutes les 2-3 h**.

---

## 10. Stratégie de démo (rappel réunion)

- **3 vidéos de démo, pas de slides** (format imposé). 1 image de présentation du projet, 3 éléments max.
- **Images floutées** pour simuler le scraping — **jamais de NSFW réel** montré au jury. Le match facial se démontre en ne montrant **que le visage** (corps flouté).
- **Environnement mock only** : faux mandat, médias de test synthétiques (adultes, pas de vraies personnes), boîte mail de démo dédiée, cible RDAP sur domaine de test contrôlé.
- Montrer aussi le **chemin mineur** sur un cas synthétique séparé qui déclenche bien le halt-and-escalate (référence loggée, zéro stockage).
- **Roadmap à pitcher** : 5-6 évolutions (enfants, comparatif, scroll étendu, V2 scan-visage…). Le jury note ~15 % sur la vision long terme.

---

## 11. Garde-fous à ne jamais violer (checklist)

- [ ] **G-1** Aucun agent ne tourne sans `Mandate.active` (base légale RGPD).
- [ ] **G-2** Le Locator reste **strictement dans le scope** — zéro surveillance de l'open web (en V1).
- [ ] **G-3** Computer use **dans Docker**, jamais sur le device de la victime.
- [ ] **G-4** Pré-check mineur **avant tout stockage** → halt + escalade PHAROS.
- [ ] **G-5** Hash perceptuel + embeddings **plutôt que** octets bruts ; on chiffre le peu qu'on retient.
- [ ] **G-6** **Gate de confirmation victime** avant tout envoi externe.
- [ ] **G-7** Chaque notice = **déclaration de bonne foi** + **ligne transparence IA** + base légale exacte (jamais inventer de montant de sanction).
- [ ] **G-8** Révocation du mandat = **purge** du dossier.
- [ ] **G-9** Zéro secret commité (`.env.local`, template dans `.env.example`).
- [ ] **G-10** Démo = **mock only**, aucune vraie victime, aucun contenu réel, aucune plateforme hostile live.
