# Rapport professionnel : Bloc E4

**RNCP 37827, Développeur.se en Intelligence Artificielle**

| | |
|---|---|
| **Candidat·e** | Noureddine BENDANOUNE |
| **Date de session** | 31/07/2026 |
| **Thème du projet** | Waterflow 2 — prédiction de potabilité de l'eau (MLOps, XGBoost via MLflow) |
| **Dépôt Git** | https://github.com/Sonicario49/waterflow2 |

---

*Ce rapport présente les compétences C14 à C19 du bloc E4 ("Mise en situation — analyser un
besoin, concevoir, développer, tester et livrer une application intégrant un service IA"), dans
l'ordre du REAC, une compétence après l'autre et sans chercher à raconter une histoire continue
entre elles. Chaque section reprend, en citation, les critères d'évaluation exacts de la grille
RNCP, puis une preuve concrète tirée du dépôt (fichier, ligne, test, capture). Le code n'est repris
dans le corps du texte que lorsqu'il est indispensable à la démonstration ; le reste est renvoyé en
annexe, hors comptage.*

*Les sorties de commandes citées ci-dessous (`docker compose up`, appels HTTP, API GitHub pour
le statut des runs CI) ont été obtenues en exécutant réellement le projet le 17/07/2026, pas
recopiées depuis une documentation antérieure.*

---

## 0. Contexte de l'épreuve E4

> **Cadre de la mise en situation (grille RNCP) :** développement d'une application intégrant
> un service d'intelligence artificielle — analyse du besoin, conception, développement, tests,
> livraison.
>
> **Livrable** : rapport professionnel individuel.
> **Évaluation** : correction du rapport professionnel + soutenance orale individuelle
> intégrant une démonstration du projet.

Là où E3 (C9-C13, cf. `RapportE_3.md`) porte sur la mise en service du modèle IA seul (API,
monitorage, tests, livraison du modèle), E4 porte sur l'**application dans son ensemble** :
l'interface Streamlit multi-pages (`ui.py`, `views/`, `dashboard_qualite.py`) et l'API FastAPI
qui la sert, du besoin fonctionnel jusqu'à la livraison. Commanditaire fictif : un réseau de
laboratoires d'analyse d'eau souhaitant remplacer une saisie manuelle de résultats par une
plateforme centralisée avec prédiction automatique de potabilité, historique par client, et un
espace de supervision qualité pour les analystes. C14 à C19 couvrent respectivement : analyser
ce besoin et le modéliser (C14), concevoir le cadre technique (C15), coordonner la réalisation
(C16), développer les composants (C17), automatiser les tests (C18), et livrer en continu (C19).

---

## 1. C14 : Analyser le besoin, rédiger les spécifications fonctionnelles et modéliser

> **Ce que le jury doit pouvoir cocher :**
> - La modélisation des données respecte un formalisme : Merise, entités-relations, etc.
> - La modélisation des parcours utilisateurs respecte un formalisme : schéma fonctionnel,
>   wireframes, etc.
> - Chaque spécification fonctionnelle couvre le contexte, les scénarios d'utilisation et les
>   critères de validation.
> - Les objectifs d'accessibilités sont directement intégrés aux critères d'acceptation des
>   user stories.
> - Les objectifs d'accessibilité sont formulés en s'appuyant sur un des standards
>   d'accessibilité : WCAG, RGAA, etc.

### 1.1 Modélisation des données (formalisme Merise)

`docs/Slidesupport/MCD.txt` (Modèle Conceptuel de Données, notation [mocodo.net](https://www.mocodo.net/))
et `MPD.txt` (Modèle Physique de Données, notation [dbdiagram.io](https://dbdiagram.io/d))
modélisent les 3 tables réelles de `data/db/WaterFlowDB.py` : `USERS` (id, username, api_key,
right, is_active), `PREDICTION` (les 9 mesures + potability + source + created_at) et
`LOGS_AUDIT` (endpoint, method, status, duration, ip, created_at), reliées par deux
associations Merise : `TRACER` (0N USERS, 01 LOGS_AUDIT) et `SOUMETTRE` (0N USERS, 11
PRELEVEMENT). Le MPD explicite les contraintes non visibles sur le MCD seul : `api_key` notée
"SHA-256 hash, jamais stocké en clair", et `audit_logs.user_id` noté "NULL après suppression
RGPD du compte (droit à l'oubli)" — la modélisation porte donc aussi les décisions de sécurité
et de conformité, pas seulement la structure des données.

### 1.2 Modélisation des parcours utilisateurs

`docs/parcours_utilisateurs.md` : 4 schémas fonctionnels Mermaid (`flowchart TD`), dérivés
directement de la logique de routage réelle (`st.navigation` selon `st.session_state.role` dans
`ui.py`, actions déclenchées dans `views/*.py`) — authentification et aiguillage par rôle
(commun à tous), puis un flowchart dédié par rôle (Client, Quality_Analyst, Admin). Chaque
nœud correspond à un écran ou un appel API réel (ex. `POST /api/ocr/lab-report`, `202/206
partiel`), pas une intention abstraite.

### 1.3 Spécifications fonctionnelles (user stories)

`docs/user_stories.md` : 12 user stories au format *En tant que / je veux / afin de*, réparties
par rôle (US-01 à US-05 Client, US-06 à US-08 Quality_Analyst, US-09 à US-11 Admin, US-12
Transverse). Chacune couvre systématiquement les 3 volets attendus : **Contexte** (contraintes
techniques, ex. US-01 précise l'absence de refresh token), **Scénario d'utilisation** (étapes
numérotées, écran par écran), et **Critères de validation** (comportements attendus, tracés
explicitement vers le test qui les couvre). Exemple concret (US-02, prédiction manuelle) :

> Requête avec 9 features valides + clé API valide → `201`, réponse contient `prediction` (0 ou
> 1), `probability_potable`, `water_status`, `client_id`. `probability_potable >= 0.37` ⟹
> `prediction = 1`. Sans header `X-API-Key` → `401`. Payload ≠ 9 features → `422`. Couvert par
> `test_measurements_predict_potable`, `test_measurements_predict_non_potable`,
> `test_measurements_bad_request`, `test_measurements_requires_api_key`.

Cette traçabilité spec ↔ test existe sur les 12 stories, pas seulement celle-ci.

### 1.4 Accessibilité intégrée aux critères d'acceptation

Les objectifs d'accessibilité ne sont pas dans une annexe séparée : chaque story porte ses
propres critères WCAG directement dans sa section "Critères de validation", formulés en
s'appuyant explicitement sur le référentiel **WCAG 2.1** (niveau AA visé), avec le numéro de
critère de succès cité (ex. US-02 : *"Accessibilité (WCAG 1.4.1 Utilisation de la couleur) : le
verdict Potable/Non Potable reste toujours accompagné du texte correspondant, jamais signalé
par la seule couleur"*). Limite assumée et documentée dans le fichier lui-même : ce sont des
**objectifs cibles** pour l'implémentation, pas un audit réalisé — aucun contrôle outillé
(contraste réel, lecteur d'écran, navigation clavier de bout en bout) n'a été mené sur
l'application Streamlit actuelle.

---

## 2. C15 : Concevoir le cadre technique de l'application

> **Ce que le jury doit pouvoir cocher :**
> - Les spécifications techniques rédigées couvrent l'architecture de l'application, ses
>   dépendances et son environnement d'exécution (langage de programmation, framework,
>   outils, etc.).
> - Les éventuels services (PaaS, SaaS, etc.) et prestataires ayant une démarche
>   éco-responsable sont favorisés lors des choix techniques.
> - Les flux de données impliqués dans l'application sont représentés par un diagramme de
>   flux de données.
> - La preuve de concept est accessible et fonctionnelle en environnement de
>   pré-production.
> - La conclusion à l'issue de la preuve de concept donne un avis précis permettant une
>   prise de décision sur la poursuite du projet.

### 2.1 Architecture, dépendances, environnement d'exécution

Langage et framework : Python 3.10 (images Docker `-slim`), backend FastAPI, frontend
Streamlit, modèle XGBoost servi via MLflow Model Registry. Architecture à 5 composants,
orchestrés par `docker-compose.yml` :

| Service | Port | Image | Rôle |
|---|---|---|---|
| `mlflow` | 5000 | `mlflow.Dockerfile` | Tracking + registre de modèles |
| `api` | 8000 | `Dockerfile` | API FastAPI (dépend de `mlflow`) |
| `streamlit` | 8501 | `ui.Dockerfile` | Interface utilisateur (dépend de `api`) |
| `prometheus` | 9090 | image officielle `prom/prometheus` | Scrape `GET /metrics` de l'API |
| `grafana` | 3000 | image officielle `grafana/grafana` | Dashboards sur les métriques Prometheus |

Environnement d'exécution : variables `MLFLOW_TRACKING_URI` (résolue à `http://mlflow:5000`
entre conteneurs, `http://127.0.0.1:5000` en dev manuel) et `API_BASE_URL` (idem pour
`streamlit` → `api`) permettent au même code de tourner en conteneur ou en local sans
modification. Deux volumes persistants : `./mlflow_data:/app` (registre MLflow + artefacts —
sans lui, tout serait perdu à chaque rebuild) et `./data/db:/app/data/db` (base SQLite). Toutes
les dépendances sont épinglées à une version exacte dans `requirements.txt` (cf. `RapportE_3.md`,
C13) — une installation stricte donne systématiquement le même environnement.

### 2.2 Choix techniques et démarche éco-responsable

Le choix a été fait dès la conception du projet d'éviter les services et l'infrastructure
énergivores : stack entièrement auto-hébergée via Docker Compose plutôt que des services
PaaS/SaaS managés tournant en permanence, images Docker `-slim` sur les 3 Dockerfiles
(`Dockerfile`, `ui.Dockerfile`, `mlflow.Dockerfile`), SQLite plutôt qu'un serveur de base de
données dédié au regard du volume réel du projet, et CI/CD sur des runners GitHub Actions à la
demande plutôt qu'un serveur d'intégration continue auto-hébergé en continu. Le seul service
tiers externe reste OCR.space (cf. `docs/diagramme_flux_donnees.md`), pour l'ingestion OCR.

### 2.3 Diagramme de flux de données

Le diagramme de flux de données du projet est versionné dans `docs/diagramme_flux_donnees.md`
(dépôt Git distant), en deux schémas Mermaid distincts, complémentaires aux parcours
utilisateurs de `docs/parcours_utilisateurs.md` (qui documentent les écrans/boutons, pas les
flux entre composants système) :

- **Vue d'ensemble (flux applicatif en direct)** : utilisateur → Streamlit UI → API FastAPI,
  puis API ↔ SQLite (lecture/écriture `users`/`prediction`/`audit_logs`), API ↔ MLflow
  (chargement du modèle Production, lecture métriques/versions), API ↔ OCR.space (upload
  fichier / texte extrait), et Prometheus → API → Grafana pour la supervision.
- **Flux hors application (entraînement)** : `data/raw/water_potability.csv` →
  `scripts/experiment.py` → MLflow, un flux batch distinct du flux applicatif live, qui
  n'implique aucune requête utilisateur.

Un tableau associé qualifie chaque flux au regard du RGPD (donnée personnelle ou non) :
`OCR.space` y est identifié comme le seul flux sortant vers un tiers externe, raison pour
laquelle `api/ocr_router.py` ne lui transmet jamais le `client_id` — seul le contenu du
document quitte l'infrastructure auto-hébergée, jamais l'identité du client.

### 2.4 Preuve de concept en environnement de pré-production

**Précision de vocabulaire, assumée** : ce projet n'a pas de serveur distant de pré-production
(staging) séparé — c'est un environnement de pré-production **local**. Ce qui justifie le terme
n'est pas l'emplacement (un serveur différent), mais le **mode d'exécution** : contrairement à
l'option "dev" du README (`uvicorn ... --reload`, services lancés à la main un par un, 3
terminaux), la stack `docker-compose.yml` fait tourner les mêmes images Docker que celles
publiées sur `ghcr.io` (cf. C13/C19), sans rechargement à chaud, orchestrées ensemble comme un
vrai déploiement le ferait — c'est ce basculement qui constitue la preuve de concept : la
démonstration que le système complet (modèle servi + API + UI + monitoring) fonctionne intégré,
packagé, pas seulement "le code tourne sur ma machine en mode développement".

5 services orchestrés ensemble (`mlflow`, `api`, `streamlit`, `prometheus`, `grafana`), lancée
avec `docker compose up --build`. Exécution réelle, tous les services démarrés et vérifiés
individuellement :

```
NAME                      SERVICE      STATUS
waterflow2-api-1          api          Up 18 seconds
waterflow2-grafana-1      grafana      Up 17 seconds
waterflow2-mlflow-1       mlflow       Up 18 seconds
waterflow2-prometheus-1   prometheus   Up 18 seconds
waterflow2-streamlit-1    streamlit    Up 18 seconds

GET http://localhost:8000/health   -> {"status":"healthy","model_loaded":true}
GET http://localhost:5000          -> 200 (MLflow)
GET http://localhost:8501          -> 200 (Streamlit)
GET http://localhost:9090/-/healthy -> Prometheus Server is Healthy.
GET http://localhost:3000/api/health -> {"database":"ok", ...} (Grafana)
```

Preuve croisée avec C11 (monitorage) : Prometheus voit bien l'API comme cible active
(`GET /api/v1/targets` → `job=waterflow2, health=up, scrapeUrl=http://api:8000/metrics`), pas
seulement un service démarré isolément — la chaîne complète (API → Prometheus) fonctionne de
bout en bout. `model_loaded: true` confirme que l'API a bien chargé un modèle réel depuis le
registre MLflow au démarrage, pas un stub.

`[Capture d'écran à insérer : docker compose up --build réussi, tous les services up]`

### 2.5 Conclusion sur la poursuite du projet

**Avis : poursuite recommandée, sous conditions précises.** La preuve de concept démontre une
viabilité technique réelle et mesurée, pas seulement déclarée : pipeline de bout en bout
fonctionnel (extraction manuelle ou OCR → prédiction → persistance → restitution), sécurité
applicative posée (clé API hachée, rôles, rate limiting, en-têtes de sécurité, RGPD), 47/47
tests passés avec 88% de couverture, et une chaîne CI/CD verte de bout en bout (validation des
données, tests, réentraînement/validation du modèle, packaging Docker) — cf. `RapportE_3.md`,
C9-C13. La performance du modèle (F1 = 0.5868, seuil de décision à 0.37) reste modeste mais
suffisante pour un premier déploiement encadré, avec une lecture assumée du compromis
precision/recall (préférer un faux négatif "non potable" à un faux négatif "potable").

Trois conditions concrètes avaient été identifiées avant un passage en production réelle. La
première est désormais résolue : les versions de `requirements.txt` sont verrouillées (`==`)
sur le jeu vérifié fonctionnel (47/47 tests, couverture 88%), après qu'un écart de version a
déjà causé un incident réel documenté (`tests/bugTrouvé_README.md`, incident 2). Deux
conditions restent ouvertes : (1) retirer le champ `ocr_raw_text` de la réponse
`POST /api/ocr/lab-report`, actuellement renvoyé en clair avec un commentaire
`# À retirer en production` déjà dans le code ; (2) automatiser la synchronisation du seuil de
décision (0.37), aujourd'hui dupliqué manuellement entre `scripts/experiment.py`,
`api/main.py` et les scripts de test. Aucune de ces conditions ne remet en cause l'architecture
ou les choix techniques du projet — ce sont des finitions avant mise en production, pas des
refontes.

---

## 3. C16 : Coordonner la réalisation technique (conduite agile / MLOps)

> **Ce que le jury doit pouvoir cocher :**
> - Les cycles, les étapes de chaque cycle, les rôles, les rituels et les outils de la méthode
>   agile appliquée sont respectés dans sa mise en place et tout au long du projet.
> - Les outils de pilotage (tableau kanban, burndown chart, backlog, etc.) sont disponibles
>   dans les conditions prévues par la méthode appliquée.
> - Les objectifs et les modalités des rituels sont partagés à toutes les parties prenantes et
>   rappelés si besoin.
> - Les éléments de pilotage sont rendus accessibles à toutes les parties du projet et ce tout
>   au long du projet, en accord avec les recommandations de la méthode de gestion de projet
>   appliquée.

### 3.1 Méthodologie appliquée : Scrum solo, sprints hebdomadaires

Le projet (1 mois de développement) a été mené en Scrum adapté au contexte d'un candidat
seul : sprints d'une semaine (~4 sprints sur la durée du projet), avec une séance hebdomadaire
le dimanche combinant revue de sprint et planification du suivant (bilan des cartes terminées,
priorisation du backlog pour la semaine à venir). Les trois rôles Scrum (Product Owner,
Scrum Master, Developer) ont été endossés par le même candidat — adaptation assumée et
explicite, pas une application Scrum d'équipe classique : la priorisation du backlog relève de
la casquette PO, le respect de la cadence hebdomadaire de la casquette Scrum Master,
l'implémentation de la casquette Developer.

### 3.2 Outil de pilotage : board Trello

`[Capture d'écran : docs/Slidesupport/trello_waterflow.png]`

Board Trello "Waterflow", structuré en 7 colonnes qui suivent le cycle de vie réel d'une tâche
de développement : `Backlog` → `Conception` → `À faire` → `En cours` → `Révision du code` →
`Test` → `Terminé`. Au moment de la capture, la colonne `Terminé` contient 14 cartes, chacune
explicitement rattachée à une compétence RNCP (ex. "Rédaction des User Stories avec critères
d'accessibilité (C14)", "Rédaction des spécifications techniques et architecture (C15)",
"Cadrage de la méthodologie Agile (C16)", "Développement de l'API REST pour le modèle IA (C9)",
"Sécurisation de l'API (Authentification & OWASP) (C9)", "Intégration de l'API dans
l'application cliente (C10)", "Développement des composants métiers et interfaces (C17)",
"Automatisation des tests du modèle IA (C12)"...), et les autres colonnes portent des cartes en
cours — preuve d'un usage continu tout au long du projet, pas d'un board créé puis abandonné.

### 3.3 Rituels : objectifs et modalités

La séance hebdomadaire du dimanche suit systématiquement le même format (revue des cartes
`Terminé`/`Test`/`Révision du code` de la semaine écoulée, puis replanification des colonnes
`À faire`/`En cours` pour la semaine suivante) — la régularité du jour, de la fréquence et du
contenu de ce rituel en constitue les modalités fixées. En contexte solo, il n'y a pas d'autres
parties prenantes à qui partager ces modalités au sens d'une équipe ; le "partage" se traduit
ici par la constance du format d'une semaine à l'autre, vérifiable sur l'historique des cartes
du board (dates de déplacement entre colonnes).

### 3.4 Accessibilité des éléments de pilotage

Le board reste consultable par le candidat tout au long du projet (interface Trello standard,
accessible au clavier, structure de liste/carte compatible lecteur d'écran). Preuve documentaire
double : la capture d'écran `docs/Slidesupport/trello_waterflow.png`, versionnée dans le dépôt
Git distant, et le board lui-même en lecture publique : https://trello.com/b/4F5OTsM2/waterflow
(lien de consultation, vérifié accessible — distinct du lien d'invitation initialement partagé,
qui permettait de rejoindre le board plutôt que simplement le consulter).

---

## 4. C17 : Développer les composants techniques et les interfaces

> **Ce que le jury doit pouvoir cocher :**
> - L'environnement de développement installé respecte les spécifications techniques du
>   projet.
> - Les interfaces sont intégrées et respectent les maquettes.
> - Les comportements des composants d'interface (validation formulaire, animations, etc.) et
>   la navigation respectent les spécifications fonctionnelles.
> - Les composants métier sont développés et fonctionnent comme prévu par les spécifications
>   techniques et fonctionnelles.
> - La gestion des droits d'accès à l'application ou à certains espaces de l'application est
>   développée et respecte les spécifications fonctionnelles.
> - Les flux de données sont intégrés dans le respect des spécifications techniques et
>   fonctionnelles.
> - Les développements sont réalisés dans le respect des bonnes pratiques d'éco-conception
>   d'une application (recommandations éco-index ou Green IT par exemple).
> - Les préconisations du top 10 d'OWASP sont implémentées dans l'application quand
>   nécessaire.
> - Des tests d'intégration ou unitaires couvrent au moins les composants métier et la gestion
>   des accès.
> - Les sources sont versionnées et accessibles depuis un dépôt Git distant.
> - La documentation technique couvre l'installation de l'environnement de développement,
>   l'architecture applicative, les dépendances, l'exécution des tests.
> - La documentation est communiquée dans un format qui respecte les recommandations
>   d'accessibilité.

### 4.1 Interfaces et maquettes

Aucune maquette visuelle séparée (Figma, wireframe) n'a été produite pour ce projet : les
spécifications d'interface ont été portées directement par les scénarios d'utilisation et
critères de validation de `docs/user_stories.md` (ex. US-01 à US-12 : quel champ, quel bouton,
quel comportement attendu à chaque étape) combinés aux flowcharts de navigation de
`docs/parcours_utilisateurs.md`. C'est ce couple scénario + flowchart qui tient lieu de
référence de conception d'interface, vérifié directement contre le comportement réel du code
(ex. US-05 exige un bouton de suppression désactivé tant que la case de confirmation n'est pas
cochée — vérifié dans `views/mes_donnees.py` et testé par
`test_ui_mes_donnees_delete_requires_confirmation`).

### 4.2 Recoupement avec C9/C10

La sécurisation OWASP (`api/auth.py`, rate limiting, en-têtes de sécurité) est déjà détaillée en
C9 (`RapportE_3.md`, 1.2) et la gestion des rôles/droits d'accès via `st.navigation` en C10
(`RapportE_3.md`, 2.1) — non dupliquées ici. Ce qui est propre à C17 :

- **Validation de formulaire** : `views/panel_test.py` refuse d'appeler l'API si une des 9
  caractéristiques vaut encore `0.0` (message d'erreur explicite plutôt qu'un appel API voué à
  échouer), et le bouton d'imputation (`mean_features.json`) ne remplace que les valeurs
  effectivement manquantes.
- **Comportements d'interface conditionnels** : `views/panel_test.py` adapte son affichage selon
  le code HTTP renvoyé par l'OCR (200/202/206) ; `views/historique.py` colore la cellule
  Potabilité sans jamais reposer sur la seule couleur (cf. C14, WCAG 1.4.1).
- **Tests unitaires/intégration sur les composants métier et les accès** : 47 tests au total
  (`tests/test_pipeline.py` + `tests/test_ui_integration.py`, cf. `RapportE_3.md` C9/C10/C12),
  dont une part significative teste spécifiquement le contrôle d'accès par rôle
  (`test_admin_route_forbidden_for_client_role`, `test_dashboard_measurements_forbidden_for_client`,
  `test_rotate_key_forbidden_for_non_admin`, `test_ui_accueil_admin_forbidden_for_client`...).

### 4.3 Éco-conception de l'application

La sobriété des ressources a été prise en compte dès les choix de développement, pas seulement
au niveau de l'infrastructure (cf. C15, 2.2) :

- **`@st.cache_data`** (`views/panel_test.py:26`, fonction `load_real_test_data`) — le jeu de
  données de test est chargé une seule fois et conservé en mémoire plutôt que relu depuis le
  disque à chaque interaction de l'utilisateur sur la page.
- **`@st.fragment`** (`views/historique.py:22`, fonction `load_and_display_history`) — seul le
  bloc d'affichage de l'historique est recalculé au clic sur "Rafraîchir l'historique", au lieu
  de faire rejouer l'intégralité du script de la page (comportement par défaut de Streamlit).
- **Filtrage côté serveur plutôt que côté client** : `GET /api/dashboard/measurements` accepte
  des filtres (`client_id`, `source`, `date_from`, `date_to`, `zone`, cf. `api/main.py`,
  `WaterFlowDB.get_all_predictions_filtered`) appliqués en SQL avant transmission — l'API ne
  transfère que les lignes demandées, jamais l'historique complet à filtrer ensuite côté
  navigateur.
- **Aucun rafraîchissement automatique** : recherche faite sur l'ensemble du code applicatif
  (`ui.py`, `views/`, `dashboard_qualite.py`), aucune boucle de polling ni auto-refresh —
  chaque appel à l'API est déclenché par une action explicite de l'utilisateur (bouton), jamais
  par un minuteur qui interrogerait le serveur en continu sans besoin réel.

---

## 5. C18 : Automatiser les phases de tests du code source (intégration continue)

> **Ce que le jury doit pouvoir cocher :**
> - La documentation pour l'utilisation de la chaîne couvre les outils, toutes les étapes, les
>   tâches et tous les déclencheurs de la chaîne.
> - Un outil de configuration et d'exécution d'une chaîne d'intégration continue est
>   sélectionné de façon cohérente avec l'environnement technique du projet.
> - La chaîne intègre toutes les étapes nécessaires et préalables à l'exécution des tests de
>   l'application (build, configurations…).
> - La chaîne exécute les tests de l'application disponibles lors de son déclenchement.
> - Les configurations sont versionnées avec les sources du projet d'application, sur un
>   dépôt Git distant.
> - La documentation de la chaîne d'intégration continue couvre la procédure d'installation,
>   de configuration et de test de la chaîne.
> - La documentation est communiquée dans un format qui respecte les recommandations
>   d'accessibilité.

Cette compétence recoupe directement C13 (`RapportE_3.md`, section 5) : même chaîne
`.github/workflows/ci.yml`, même documentation `docs/CI_CD.md`. L'angle propre à C18 porte
spécifiquement sur l'étape "Run tests" : outil retenu (`pytest`, cohérent avec le reste de la
stack Python du projet), étapes préalables nécessaires avant de pouvoir exécuter les tests
(`Checkout` → `Set up Python` → `Install dependencies` → `Validate raw data`), et exécution
réelle confirmée verte sur le dernier run (`6ba34ba`, vérifié via l'API GitHub : étape "Run
tests (coverage gate: 80% minimum on api/ + data.db/)" → `completed`/`success`), avec le gate
de couverture qui fait échouer la chaîne si elle retombe sous 80% (cf. C12, `RapportE_3.md`
4.3).

---

## 6. C19 : Créer un processus de livraison continue de l'application

> **Ce que le jury doit pouvoir cocher :**
> - La documentation pour l'utilisation de la chaîne couvre toutes les étapes de la chaîne,
>   les tâches et tous les déclencheurs disponibles.
> - Le ou les fichiers de configuration de la chaîne sont correctement reconnus et exécutés
>   par le système.
> - La ou les étapes de packaging (compilation, minification, build de containers, etc.) de
>   l'application sont intégrées à la chaîne et s'exécutent sans erreur.
> - L'étape de livraison (pull request par exemple) est intégrée et exécutée une fois la ou
>   les étapes de packaging validées.
> - Les sources de la chaîne sont versionnées et accessibles depuis le dépôt Git distant du
>   projet d'application.
> - La documentation de la chaîne de livraison continue couvre la procédure d'installation, de
>   configuration et de test de la chaîne.
> - La documentation est communiquée dans un format qui respecte les recommandations
>   d'accessibilité.

Cette compétence recoupe C13 (packaging Docker, `RapportE_3.md` section 5.4) et y ajoute une
étape de livraison réellement automatisée : publication des 3 images du projet
(`waterflow2-api`, `waterflow2-mlflow`, `waterflow2-streamlit`) sur GitHub Container Registry,
exécutée uniquement une fois le packaging validé et uniquement sur push vers `main`. Confirmé
en exécution réelle, pas seulement en configuration : le run `6ba34ba` est vert de bout en bout
(11/11 étapes, vérifié via l'API GitHub), et les 3 images sont effectivement publiées et
consultables (`github.com/Sonicario49/waterflow2/pkgs/container/waterflow2-{api,mlflow,streamlit}`).

Le **déploiement** de ces images reste volontairement manuel (pull request revue et fusionnée à
la main, cf. `docs/CI_CD.md`) — distinction assumée entre publier un artefact (désormais
automatisé) et le déployer en production (resté un acte humain).

---

## 7. Difficultés rencontrées et conclusion

**`README.md` inexploitable en l'état (C17).** Le fichier initial mélangeait une veille
technologique sur MLflow et des commandes `curl` en vrac, sans même l'étape
`pip install -r requirements.txt` en premier — un nouveau développeur qui l'aurait suivi
littéralement aurait échoué à la première commande. Résolu par une réécriture complète
(installation en premier, 2 options de lancement, tableau d'architecture) et le déplacement du
contenu de veille vers `docs/veille_mlflow.md`, pour ne pas polluer un document censé rester un
guide d'installation.

**Aucune preuve d'éco-responsabilité ni d'éco-conception préexistante (C15, C17).** Une
recherche explicite dans tout le dépôt n'a rien trouvé sur ces deux critères avant qu'on les
traite. Plutôt que de rédiger une justification a posteriori générique, chaque affirmation a été
vérifiée contre du code réel (images `-slim`, `@st.cache_data`, `@st.fragment`, filtrage côté
serveur, absence de polling) et la question de l'intention d'origine posée explicitement plutôt
que supposée.

**Aucun artefact de méthode agile trouvé initialement (C16).** Une vérification via l'API
GitHub (issues, milestones, Projects) n'a rien donné — ni board, ni backlog visible depuis le
dépôt. La preuve réelle (board Trello + Scrum solo hebdomadaire) n'est apparue qu'après coup, et
son premier lien de partage était un lien **d'invitation** (permettant de rejoindre le board),
pas un lien de consultation — remplacé par un lien public en lecture seule avant d'être intégré
au rapport, pour ne pas exposer un board personnel modifiable publiquement.

**Terminologie "pré-production" à préciser (C15).** Ce projet n'a pas de serveur de staging
distant séparé. Plutôt que de laisser sous-entendre l'inverse, le rapport assume explicitement
qu'il s'agit d'un pré-production **local** — justifié par le mode d'exécution (images packagées
sans rechargement à chaud, orchestrées ensemble) et non par l'emplacement.

**Étape de livraison initialement incomplète (C19).** Le premier ajout à la CI ne publiait que
l'image API sur `ghcr.io`. Étendue aux 3 images du projet (mlflow, streamlit) après coup, avec
vérification réelle avant intégration (builds locaux des 2 nouveaux Dockerfiles testés avec
succès), puis confirmation du run CI réel vert de bout en bout et des 3 images effectivement
publiées et consultables.

**Conclusion.** L'application dans son ensemble (pas seulement le modèle, cf. E3) est
analysée depuis le besoin fonctionnel (C14 : MCD/MPD Merise, parcours utilisateurs, 12 user
stories tracées vers des tests, accessibilité WCAG intégrée nativement), conçue techniquement
(C15 : architecture documentée, choix de sobriété assumés, diagramme de flux de données, preuve
de concept vérifiée en exécution réelle), pilotée avec une méthode adaptée au contexte solo
(C16 : Scrum hebdomadaire, board Trello vérifiable), développée dans le respect des
spécifications et de l'éco-conception (C17), testée automatiquement (C18) et livrée en continu
jusqu'à la publication réelle des images Docker (C19). Chaque affirmation de ce rapport a été
revérifiée contre des preuves d'exécution réelles plutôt que des affirmations déclarées, avec
plusieurs corrections apportées en cours de route (README, incohérences de comptage,
placeholders obsolètes).

---

## Annexe : préparation de la soutenance orale (15 min)

- **Repo Git accessible en amont** : https://github.com/Sonicario49/waterflow2
- **Démonstration prévue** : (1) montrer `docs/Slidesupport/MCD.txt`/`MPD.txt` et une story de
  `docs/user_stories.md` avec son test associé ouvert côte à côte, (2) montrer le board Trello
  en direct (colonnes, cartes taguées par compétence), (3) `docker compose up --build` et
  vérifier les 5 services + `http://localhost:8000/health`, (4) montrer les 3 images publiées
  sur `github.com/Sonicario49/waterflow2/pkgs/container/waterflow2-api` (et mlflow/streamlit).
- **Minutage suggéré** : 2 min contexte, puis ~2-3 min par compétence (C14 à C19), 1 min
  conclusion.

**Questions probables du jury et réponses préparées :**

**Q : Pourquoi aucune maquette visuelle (Figma, wireframe) ?**
Les spécifications d'interface ont été portées par les scénarios d'utilisation détaillés de
`docs/user_stories.md` (quel champ, quel bouton, quel comportement) combinés aux flowcharts de
navigation — choix assumé de ne pas produire un artefact de conception séparé pour un projet
solo à ce stade, plutôt qu'un oubli non documenté.

**Q : Un Scrum solo, avec les 3 rôles endossés par la même personne — en quoi c'est un vrai
Scrum ?**
La structure (sprints réguliers, backlog priorisé, revue + planification à cadence fixe,
board Kanban avec colonnes reflétant le cycle de vie réel d'une tâche) est respectée ; ce qui
change par rapport à un Scrum d'équipe, c'est qu'une seule personne porte les 3 casquettes —
adaptation explicitement assumée dans le rapport, pas présentée comme un vrai Scrum d'équipe.

**Q : "Pré-production" alors qu'il n'y a pas de serveur distant — n'est-ce pas trompeur ?**
Non, si le terme est précisé (ce que fait le rapport) : ce qui distingue la pré-production du
développement ici n'est pas l'emplacement mais le mode d'exécution — images packagées, sans
rechargement à chaud, orchestrées ensemble comme un vrai déploiement le ferait, par opposition
au mode `--reload` lancé à la main service par service.

**Q : Les images Docker publiées servent à quoi concrètement si le déploiement reste manuel ?**
Elles rendent l'artefact prêt à être déployé n'importe où qui sait tirer une image Docker (un
VPS, Render, un cluster) sans avoir à rebuild depuis les sources — la publication (automatisée)
et le déploiement (décision humaine, pull request revue) sont deux étapes volontairement
séparées.

---

## Annexe technique (hors comptage)

`[À COMPLÉTER si nécessaire pour la soutenance.]`
