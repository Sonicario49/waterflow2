# Rapport professionnel : Bloc E4

**RNCP 37827, Développeur.se en Intelligence Artificielle**

| | |
|---|---|
| **Candidat·e** | Noureddine BENDANOUNE |
| **Date de session** | `[À COMPLÉTER]` |
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

*Ce fichier est un plan de rédaction : chaque section contient les critères à satisfaire et des
repères `[À COMPLÉTER]` pointant vers les preuves probables déjà identifiées dans le dépôt. Le
contenu rédigé viendra remplacer ces repères compétence par compétence — on commence par C15.*

---

## 0. Contexte de l'épreuve E4

> **Cadre de la mise en situation (grille RNCP) :** développement d'une application intégrant
> un service d'intelligence artificielle — analyse du besoin, conception, développement, tests,
> livraison.
>
> **Livrable** : rapport professionnel individuel.
> **Évaluation** : correction du rapport professionnel + soutenance orale individuelle
> intégrant une démonstration du projet.

`[À COMPLÉTER : 1 paragraphe de contexte — l'application concernée est l'ensemble UI Streamlit
+ API FastAPI de Waterflow 2 (pas seulement le modèle, contrairement à E3). Préciser le
commanditaire fictif/réel et le périmètre couvert par C14-C19 par rapport à ce qui a déjà été
traité en E3 (C9-C13, mise en service du modèle).]`

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

`[À COMPLÉTER : s'appuyer sur les preuves déjà présentes dans le dépôt —
docs/Slidesupport/MCD.txt + MPD.txt (formalisme Merise/entités-relations),
docs/parcours_utilisateurs.md (4 flowcharts Mermaid : Auth, Client, Quality_Analyst, Admin —
déjà exportés en PNG dans docs/Slidesupport/ pour les slides), docs/user_stories.md
(spécifications fonctionnelles + critères WCAG par story). Vérifier que chaque user story
couvre bien contexte/scénarios/critères de validation, et que les critères d'accessibilité y
sont intégrés nativement (pas en annexe séparée).]`

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

`[À COMPLÉTER : décrire l'architecture réelle à partir de docker-compose.yml (5 services :
mlflow, api, streamlit, prometheus, grafana), des 3 Dockerfiles (Dockerfile, ui.Dockerfile,
mlflow.Dockerfile — langage Python 3.10-slim, dépendances via requirements.txt), et de
l'environnement d'exécution (ports, variables d'environnement MLFLOW_TRACKING_URI/
API_BASE_URL, volumes persistants ./mlflow_data et ./data/db). Un schéma d'architecture
(composants + ports) serait utile ici, distinct du diagramme de flux de données ci-dessous.]`

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

`[À COMPLÉTER : la stack docker-compose.yml sert de preuve de concept — décrire comment la
lancer (docker compose up --build), ce qui la rend "accessible et fonctionnelle" (5 services
démarrés, ports exposés, healthcheck /health, modèle chargé depuis MLflow Production).
Capture d'écran ou sortie de commande réelle à l'appui.]`

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

`[À COMPLÉTER : ce chapitre recoupe largement C9 (OWASP, déjà traité dans RapportE_3.md) et
C10 (composants Streamlit, gestion des rôles/droits d'accès via st.navigation, déjà traité
dans RapportE_3.md). Ne pas dupliquer intégralement — renvoyer vers ces sections et ajouter ce
qui est spécifique à C17 : validation de formulaire (ex. panel_test.py, refus si une valeur
reste à 0.0), tests unitaires/intégration sur les composants métier (tests/test_pipeline.py +
tests/test_ui_integration.py).]`

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

`[À COMPLÉTER : recoupe directement C13 (déjà traité dans RapportE_3.md, section 5) — même
pipeline .github/workflows/ci.yml, même docs/CI_CD.md. Renvoyer vers cette section plutôt que
de tout réécrire ; ajouter uniquement l'angle propre à C18 (étape de test elle-même, pas le
volet modèle/livraison déjà couvert en C13/C19).]`

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

`[À COMPLÉTER : recoupe C13 (packaging Docker, déjà traité dans RapportE_3.md section 5.4) et
souligne le point déjà documenté honnêtement : pas d'étape de publication/déploiement
automatisée, la livraison reste une pull request revue manuellement (docs/CI_CD.md). Point de
vigilance repris de l'ancien docs/checklist_C9_C19.md (désormais nettoyé) : vérifier si
"l'étape de livraison (pull request)" doit être interprétée comme suffisante telle quelle, ou
si le critère attend une automatisation de la PR elle-même (ex. action GitHub qui ouvre une PR
automatiquement) — à clarifier avant de cocher.]`

---

## 7. Difficultés rencontrées et conclusion

`[À COMPLÉTER une fois C14 à C19 rédigées : reprendre les difficultés réelles propres à ce
bloc (distinctes de celles déjà listées dans RapportE_3.md pour E3) et conclure sur
l'ensemble C14-C19.]`

---

## Annexe : préparation de la soutenance orale (15 min)

`[À COMPLÉTER : repo Git, scénario de démonstration, minutage, questions probables du jury —
même structure que l'annexe de RapportE_3.md.]`

---

## Annexe technique (hors comptage)

`[À COMPLÉTER si nécessaire pour la soutenance.]`
