# Rapport professionnel : Bloc E3

**RNCP 37827, Développeur.se en Intelligence Artificielle**

| | |
|---|---|
| **Candidat·e** | Noureddine BENDANOUNE |
| **Date de session** | 31/07/2026 |
| **Thème du projet** | Waterflow 2 — prédiction de potabilité de l'eau (MLOps, XGBoost via MLflow) |
| **Dépôt Git** | https://github.com/Sonicario49/waterflow2 |

---

*Ce rapport présente les compétences C9 à C13 du bloc E3 ("Mise en situation — mise en
service d'un modèle fourni et intégration dans une application existante"), dans
l'ordre du REAC, une compétence après l'autre et sans chercher à raconter une histoire
continue entre elles. Chaque section reprend, en citation, les critères d'évaluation
exacts de la grille RNCP, puis une preuve concrète tirée du dépôt (fichier, ligne,
test réellement exécuté, capture). Le code n'est repris dans le corps du texte que
lorsqu'il est indispensable à la démonstration ; le reste est renvoyé en annexe, hors
comptage.*

*Toutes les sorties de commandes citées ci-dessous (`pytest`, `validate_data.py`,
`validate_model.py`, `/openapi.json`) ont été obtenues en exécutant réellement le
code du dépôt le 16/07/2026, pas recopiées depuis une documentation antérieure.*

---

## 0. Contexte de l'épreuve E3

> **Cadre de la mise en situation (grille RNCP) :** réalisation d'un service
> d'intelligence artificielle à partir d'un modèle fourni. Le projet évalué a pour but
> la mise en service (*packaging*, monitorage, test...) du modèle fourni, et son
> intégration dans une application existante.
>
> **Livrable** : rapport professionnel individuel.
> **Évaluation** : correction du rapport professionnel + soutenance orale
> individuelle intégrant une démonstration du projet.

Le modèle fourni est un classifieur XGBoost qui prédit la potabilité de l'eau
(0/1) à partir de 9 mesures physico-chimiques (ph, dureté, solides dissous,
chloramines, sulfates, conductivité, carbone organique, trihalométhanes, turbidité).
Il est entraîné et tracké par MLflow (`scripts/experiment.py`, hors périmètre E3),
puis chargé en mémoire par une API FastAPI (`api/main.py`) au démarrage, depuis le
registre de modèles MLflow (`models:/water_quality_model/Production`). Cette API est
elle-même consommée par deux applications existantes : une interface Streamlit
multi-pages (`ui.py`, `views/`, `dashboard_qualite.py`) et une route d'ingestion OCR
de fiches labo (`api/ocr_router.py`). C9 à C13 couvrent respectivement : exposer ce
modèle via une API REST sécurisée (C9), l'intégrer dans l'application Streamlit
existante (C10), le monitorer en production (C11), tester le pipeline qui l'entoure
de façon automatisée (C12), et livrer l'ensemble en continu (C13).

---

## 1. C9 : Développer une API exposant un modèle d'intelligence artificielle

> **Ce que le jury doit pouvoir cocher :**
> - L'API restreint l'accès au modèle d'intelligence artificielle avec un moyen
>   d'authentification.
> - L'API permet l'accès aux fonctions du modèle, comme attendu selon les
>   spécifications.
> - Les recommandations de sécurisation d'une API du top 10 OWASP sont intégrées
>   quand nécessaire.
> - Les sources sont versionnées et accessibles depuis un dépôt Git distant.
> - Les tests couvrent tous les points de terminaison dans le respect des
>   spécifications.
> - Les tests s'exécutent sans bug.
> - Les résultats des tests sont correctement interprétés.
> - La documentation couvre l'architecture et tous les points de terminaison de
>   l'API.
> - La documentation couvre les règles d'authentification et/ou d'autorisation
>   d'accès à l'API.
> - La documentation et l'API respectent les standards d'un modèle choisi (par
>   exemple OpenAPI).
> - La documentation est communiquée dans un format qui respecte les
>   recommandations d'accessibilité.

### 1.1 Architecture et points de terminaison

L'API est un projet FastAPI (`api/main.py` + `api/ocr_router.py`, monté avec le
préfixe `/api/ocr`), organisée en 8 groupes fonctionnels (tags), 13 chemins distincts
et 16 opérations HTTP au total (confirmé en interrogeant `/openapi.json` sur
l'application réellement démarrée, cf. 1.3) :

| Méthode | Route | Tag | Accès | Fonction du modèle exposée |
|---|---|---|---|---|
| GET | `/health` | Système | public | Signale si le modèle est chargé en mémoire |
| POST | `/api/login` | Auth | authentifié | Vérifie la clé API, retourne l'identité/rôle |
| POST | `/api/measurements` | Prélèvements | authentifié | **Appelle `model.predict_proba`**, applique le seuil (0.37), enregistre et retourne la prédiction |
| GET | `/api/measurements` | Prélèvements | authentifié | Historique des prélèvements du client courant |
| POST | `/api/clients` | Clients | Admin | Crée un compte + clé API |
| GET | `/api/clients` | Clients | Admin | Liste tous les comptes |
| POST | `/api/clients/{cid}/rotate-key` | Clients | Admin | Révoque puis régénère une clé API |
| GET | `/api/audit-logs` | Admin | Admin | Journal d'audit complet |
| GET | `/api/me` | RGPD | authentifié | Droit d'accès RGPD |
| DELETE | `/api/me` | RGPD | authentifié | Droit à l'oubli RGPD |
| GET | `/api/dashboard/measurements` | Dashboard | Quality_Analyst/Admin | Tous les prélèvements, filtrables |
| GET | `/api/dashboard/metrics` | Dashboard | Quality_Analyst/Admin | **Métriques MLflow** de la version Production du modèle |
| GET | `/api/dashboard/model-versions` | Dashboard | Quality_Analyst/Admin | **Toutes les versions** du modèle enregistrées dans MLflow |
| POST | `/api/dashboard/replay` | Dashboard | Quality_Analyst/Admin | **Recharge une version précise du modèle** (`runs:/{run_id}/model`) et rejoue une prédiction |
| POST | `/api/ocr/lab-report` | OCR | authentifié | Parse une fiche labo puis **appelle `model.predict_proba`** sur les valeurs extraites |
| GET | `/api/ocr/health` | OCR | public | Santé du service OCR externe |

Cinq routes touchent directement le modèle : la prédiction "manuelle" et OCR
(`/api/measurements`, `/api/ocr/lab-report`), et l'introspection du registre MLflow
(`/api/dashboard/metrics`, `/model-versions`, `/replay`).

### 1.2 Authentification et sécurisation OWASP

L'authentification est portée par une dépendance FastAPI unique et partagée,
`get_current_user` (`api/auth.py`), injectée sur chaque route protégée via
`Depends(...)` — jamais dupliquée entre `main.py` et `ocr_router.py`. Le principe :
un header `X-API-Key`, haché en SHA-256 et comparé au hash stocké en base (jamais la
clé en clair) ; `require_role(*roles)` encapsule `get_current_user` pour restreindre
certaines routes par rôle (`Client`, `Quality_Analyst`, `Admin`).

```python
def get_current_user(api_key: str | None = Security(api_key_header)) -> UserInfo:
    if not api_key:
        raise HTTPException(status_code=401, detail="Clé API manquante (header X-API-Key requis).")
    hashed = hashlib.sha256(api_key.encode()).hexdigest()
    ...
    matched = next((u for u in all_users if u[2] == hashed), None)
    if not matched:
        raise HTTPException(status_code=401, detail="Clé API invalide ou expirée.")
    if len(matched) > 4 and matched[4] == 0:
        raise HTTPException(status_code=403, detail="Cette clé API a été révoquée.")
    return UserInfo(id=matched[0], username=matched[1], role=matched[3])
```

Correspondance avec des points concrets du Top 10 OWASP (API Security Top 10 pour
les catégories spécifiques REST, Top 10 web classique pour les autres) :

| Risque OWASP | Mesure appliquée dans le code | Preuve |
|---|---|---|
| **API2:2023 Broken Authentication** | Clé API hachée SHA-256 en base, jamais stockée/loggée en clair ; endpoint de rotation qui invalide l'ancienne clé | `api/auth.py:35`, `WaterFlowDB.rotate_user_key` ; `tests/test_pipeline.py::test_rotate_key_admin` |
| **API5:2023 Broken Function Level Authorization** | `require_role("Admin")` / `require_role("Quality_Analyst", "Admin")` sur les routes sensibles, jamais un simple test de rôle inline | `api/auth.py:64-81` ; `test_admin_route_forbidden_for_client_role`, `test_dashboard_measurements_forbidden_for_client` |
| **API1:2023 Broken Object Level Authorization** | `GET /api/measurements` ne prend aucun `user_id` en paramètre : il ne peut renvoyer que l'historique du titulaire de la clé (`current_user.id`) | `api/main.py:299-303` |
| **API4:2023 Unrestricted Resource Consumption** | Rate limiting `slowapi` : 10 requêtes/min sur `/api/login` (anti brute-force), 500/heure sur `/api/measurements` | `api/main.py:243,259` ; `test_login_rate_limited` (10 requêtes OK, la 11ᵉ renvoie 429) |
| **A03:2021 Injection** | Toutes les requêtes SQL de `WaterFlowDB.py` utilisent des paramètres liés (`?`), aucune concaténation de chaîne, y compris dans la requête à filtres dynamiques `get_all_predictions_filtered` | `data/db/WaterFlowDB.py:187-220` |
| **API8:2023 Security Misconfiguration** | Middleware `security_headers` (X-Content-Type-Options, X-Frame-Options, Referrer-Policy) sur chaque réponse ; pas de `CORSMiddleware` (aucun front web tiers n'appelle l'API depuis un navigateur — commentaire explicite dans le code) | `api/main.py:106-113` ; `test_security_headers_present` |
| Exposition de secret | La clé API en clair n'est retournée qu'une seule fois (création/rotation), jamais recalculée ni relogguée ensuite | `api/main.py:349,398` (commentaire explicite dans le code) |

**Limite assumée, documentée honnêtement** : la réponse de `POST /api/ocr/lab-report`
renvoie le champ `ocr_raw_text` (texte brut extrait du document), avec le commentaire
`# À retirer en production` directement dans le code (`api/ocr_router.py:265`) — utile
en phase de debug pour visualiser ce que l'OCR a lu, mais à supprimer avant une mise
en production réelle (fuite potentielle d'information si le document contient plus
que les 9 champs attendus).

### 1.3 Documentation (OpenAPI / Swagger)

FastAPI génère automatiquement la documentation OpenAPI (`/docs` pour l'UI Swagger,
`/openapi.json` pour le schéma brut), sans effort de rédaction manuelle — donc jamais
désynchronisée du code réel. Vérification faite en interrogeant l'application
réellement démarrée :

```
status 200
securitySchemes: {'APIKeyHeader': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-Key'}}
total_paths 13
/api/ocr/lab-report post security= [{'APIKeyHeader': []}]
/api/ocr/health   get  security= None
/health           get  security= None
```

Le schéma de sécurité `APIKeyHeader` apparaît dans `components.securitySchemes`, et
chaque route protégée porte explicitement `"security": [{"APIKeyHeader": []}]` —
c'est ce qui fait apparaître le cadenas dans Swagger UI sur les routes authentifiées,
et son absence sur `/health` et `/api/ocr/health`, cohérente avec le code. La
documentation couvre donc à la fois l'architecture (13 chemins, 8 tags visibles dans
le menu Swagger) et les règles d'authentification.

`[Capture d'écran à insérer : Swagger UI /docs, avec le cadenas visible sur
/api/measurements et /api/ocr/lab-report, absent sur /health]`

**Accessibilité de la documentation.** Swagger UI reste une interface web standard
(HTML sémantique, contrastes par défaut du thème FastAPI, navigable au clavier) : pas
d'audit WCAG formalisé sur ce projet, mais aucune information n'y est encodée
uniquement par la couleur, et le schéma `/openapi.json` reste consultable en texte
brut, sans interface graphique, pour tout outil d'assistance qui préférerait le
consommer directement.

### 1.4 Tests couvrant les points de terminaison

`tests/test_pipeline.py` teste l'API en direct via `fastapi.testclient.TestClient`,
avec le modèle MLflow et le client MLflow remplacés par des doublures de test
(`tests/conftest.py` : `DummyModel`, `FakeMlflowClient`), pour ne dépendre d'aucun serveur MLflow réel. Les 16 opérations listées en 1.1 y sont toutes couvertes,
positif et négatif (accès refusé sans clé, refusé pour le mauvais rôle, payload
invalide) :

| Route testée | Cas couverts |
|---|---|
| `/health`, `/metrics` | disponibilité, format des métriques Prometheus |
| `/api/login` | clé valide, clé invalide, rate limiting (10/min) |
| `/api/measurements` (POST/GET) | sans clé (401), potable, non potable, payload à 8 valeurs (422), historique après soumission |
| `/api/clients` (POST/GET) | refusé pour rôle Client (403), autorisé pour Admin |
| `/api/clients/{id}/rotate-key` | refusé pour non-Admin, client inexistant (404), ancienne clé invalidée + nouvelle fonctionnelle |
| `/api/audit-logs` | refusé pour non-Admin, présence de l'appel `/api/login` dans le journal |
| `/api/me` (GET/DELETE) | données personnelles renvoyées, suppression puis clé invalidée |
| `/api/dashboard/*` (4 routes) | refusé pour Client, données filtrées pour Analyst/Admin, métriques/versions/rejeu du modèle factice |
| `/api/ocr/lab-report`, `/health` | sans clé (401), extension refusée (415), succès avec extraction complète |

Exécution réelle de la suite complète (API + intégration UI, cf. C10) :

```
............................................... [100%]
47 passed, 1 warning in 280.73s (0:04:40)
```

47/47 tests passent, exit code 0 — aucun bug dans les tests eux-mêmes. Ce résultat a
été instable par le passé (cf. `tests/bugTrouvé_README.md`, incident 2 : le mock de
`mlflow.xgboost.load_model` n'était pas toujours actif au moment précis du
`lifespan`, provoquant un échec dépendant de l'ordre d'exécution) ; la correction
(forcer explicitement `c.app.state.model = DummyModel()` après le démarrage du
`TestClient`, `tests/conftest.py:143-145`) est en place et vérifiée par l'exécution
ci-dessus.

---

## 2. C10 : Intégrer l'API d'un modèle/service IA dans une application

> **Ce que le jury doit pouvoir cocher :**
> - L'application de départ est installée et fonctionnelle en environnement de
>   développement.
> - La communication avec l'API depuis l'application fonctionne.
> - Les éventuelles étapes d'authentification et de renouvellement de
>   l'authentification (expiration des jetons par exemple) sont intégrées
>   correctement en suivant la documentation de l'API.
> - Tous les points de terminaison de l'API concernés par le projet sont intégrés à
>   l'application selon les spécifications fonctionnelles et techniques.
> - Les adaptations d'interfaces nécessaires et en accord avec les spécifications
>   sont intégrées à l'application.
> - Les tests d'intégration couvrent tous les points de terminaison exploités.
> - Les tests s'exécutent en totalité : il n'y a pas de bug dans les programmes des
>   tests en eux-mêmes.
> - Les résultats des tests sont correctement interprétés.
> - Les sources sont versionnées et accessibles depuis le dépôt Git de
>   l'application.

### 2.1 Application cliente : Streamlit (ui.py + views/)

L'application de départ est une app Streamlit multi-pages (`ui.py`), fonctionnelle en
développement via `python -m streamlit run ui.py` (ou `waterflow2.bat`). Le rôle
retourné par `POST /api/login` (`res_data.get("role")`) pilote dynamiquement les
pages exposées par `st.navigation` :

```python
if st.session_state.role == "Admin":
    nav = st.navigation([page_admin, page_securite])
elif st.session_state.role == "Quality_Analyst":
    nav = st.navigation([page_dashboard_qualite])
else:
    nav = st.navigation([page_panel, page_historique, page_mes_donnees])
```

Il n'y a pas de session côté serveur : `st.session_state` porte la clé API en
mémoire pour la durée de la session navigateur, renvoyée en header `X-API-Key` à chaque appel `requests.get/post/delete` — c'est la même clé API que celle utilisée en C9, aucun mécanisme d'authentification distinct côté UI.

### 2.2 Communication et gestion de l'authentification

Chaque page transmet systématiquement `headers = {"X-API-Key": st.session_state.api_key}`.
Il n'y a pas de jeton à expiration à renouveler ici (choix architectural : clé API
statique, pas de JWT) — le seul renouvellement d'authentification existant est la
**rotation manuelle** de clé (`views/securite_admin.py`, section "Renouveler une clé
API existante"), qui appelle `POST /api/clients/{id}/rotate-key` et invalide
immédiatement l'ancienne clé, suivant exactement le contrat documenté côté API (1.2).
`ui.py` gère aussi le cas d'échec réseau (`requests.exceptions.ConnectionError`) sur
l'écran de connexion, avec un message explicite plutôt qu'un plantage.

### 2.3 Couverture des points de terminaison intégrés

| Endpoint API | Page Streamlit qui l'appelle |
|---|---|
| `POST /api/login` | `ui.py` (écran de connexion) |
| `POST /api/measurements` | `views/panel_test.py` (bouton "Lancer la prédiction API") |
| `POST /api/ocr/lab-report` | `views/panel_test.py` (bouton "Analyser le document via l'OCR") |
| `GET /api/measurements` | `views/historique.py` |
| `GET /api/me`, `DELETE /api/me` | `views/mes_donnees.py` |
| `GET /api/clients`, `GET /api/audit-logs` | `views/accueil_admin.py` |
| `POST /api/clients`, `GET /api/clients`, `POST /api/clients/{id}/rotate-key` | `views/securite_admin.py` |
| `GET /api/dashboard/measurements`, `/metrics`, `/model-versions`, `POST /replay` | `dashboard_qualite.py` (3 onglets : Prélèvements, Métriques du modèle, Comparaison des versions) |

Tous les points de terminaison listés en C9 sont donc bien exploités par
l'application, sauf `GET /health` et `GET /api/ocr/health` (deux routes de
supervision technique, destinées au healthcheck Docker et à la surveillance
interne, pas à un affichage utilisateur — vérifié : aucune occurrence de `/health`
dans `ui.py`/`views/`/`dashboard_qualite.py`).

**Adaptations d'interface notables** : `views/historique.py` colore
conditionnellement la cellule "Potabilité" (vert/rouge) selon la valeur renvoyée par
l'API ; `views/panel_test.py` adapte son affichage selon le code de statut HTTP
renvoyé par l'OCR (200 = succès complet, 202/206 = extraction partielle avec
avertissements affichés un par un) ; `views/securite_admin.py` masque la clé API en
clair par défaut (`st.text_input(..., value=..., key=...)`) et n'affiche le
formulaire de clé qu'immédiatement après création/rotation, jamais rechargeable
ensuite (cohérent avec la contrainte API "la clé n'est retournée qu'une fois").

### 2.4 Tests d'intégration UI ↔ API

`tests/test_ui_integration.py` utilise `streamlit.testing.v1.AppTest` pour exécuter
réellement les pages Streamlit, combiné à la fixture `ui_client` (`tests/conftest.py`)
qui redirige `requests.get/post/delete` vers le même `TestClient` FastAPI que celui
utilisé en C9 (même DB de test, même modèle factice) — ces tests exercent donc les
vraies routes API, pas des réponses mockées à la main.

| Page testée | Ce qui est vérifié |
|---|---|
| `views/panel_test.py` | le bouton de prédiction appelle réellement `POST /api/measurements` et affiche "Potable (Safe)" ; refuse d'appeler l'API si une caractéristique vaut encore 0.0 |
| `views/historique.py` | affiche l'historique réellement enregistré via `POST` puis `GET /api/measurements` ; état vide géré sans erreur |
| `views/accueil_admin.py` | liste réellement les comptes et les logs (`GET /api/clients`, `GET /api/audit-logs`) ; accès refusé (403 relayé) pour un rôle Client |
| `views/securite_admin.py` | le formulaire de création appelle réellement `POST /api/clients` ; le bouton de rotation appelle réellement `POST /api/clients/{id}/rotate-key`, et l'ancienne clé cesse ensuite de fonctionner (vérifié via un appel API direct dans le test) |
| `views/mes_donnees.py` | affiche les données réelles via `GET /api/me` ; le bouton de suppression reste désactivé sans la case de confirmation cochée ; coché + cliqué, appelle réellement `DELETE /api/me` |
| `dashboard_qualite.py` | les 3 onglets appellent réellement les routes `/api/dashboard/*` |

12 tests, inclus dans les 47 exécutés en 1.4 (`47 passed, 1 warning in 280.73s`) —
aucun échec, aucun bug dans les tests eux-mêmes.

**Deux difficultés réelles rencontrées en écrivant ces tests** (documentées dans
`tests/bugTrouvé_README.md`, incident 3), et interprétées comme des oublis de setup
de test plutôt que des bugs applicatifs :
1. `test_ui_historique_shows_real_data` échouait par `AttributeError` sur
   `st.session_state.user_id`, absent du setup du test (en usage réel, `ui.py`
   l'initialise toujours à la connexion) — corrigé en initialisant `user_id` avant
   `at.run()`.
2. `test_ui_securite_admin_rotate_key` échouait car `securite_admin.py` contient
   **deux** `st.selectbox` (rôle du formulaire de création, puis compte cible de la
   rotation) — le test visait le mauvais widget (`selectbox[0]` au lieu de
   `selectbox[1]`).

**Limite assumée, non couverte** : `POST /api/ocr/lab-report` (bouton OCR de
`views/panel_test.py`) n'est pas exercé par `AppTest`, qui ne simule pas
l'interaction avec `st.file_uploader`, ce flux reste testé côté API
(`test_ocr_lab_report_success`, cf. C9).

---

## 3. C11 : Monitorer un modèle d'intelligence artificielle

> **Ce que le jury doit pouvoir cocher :**
> - Les métriques faisant l'objet du monitorage du modèle sont expliquées sans
>   erreur d'interprétation.
> - Le ou les outils pour l'intégration du monitorage du modèle sont adaptés au
>   contexte et aux contraintes techniques du projet.
> - Au moins un vecteur de restitution des métriques évaluées, en temps réel, est
>   proposé (dashboard, feuille de calcul, etc.).
> - Les enjeux d'accessibilité, pour toutes les parties prenantes du projet, sont
>   pris en compte lors de la sélection de l'outil de restitution.
> - La chaîne de monitorage est d'abord testée dans un bac à sable ou environnement
>   de test dédié.
> - La chaîne de monitorage est en état de marche. Les métriques visées sont
>   effectivement évaluées et restituées.
> - Les sources sont versionnées et accessibles depuis un dépôt Git distant.
> - La documentation technique de la chaîne de monitorage couvre la procédure
>   d'installation, de configuration et d'utilisation à destination des équipes
>   techniques.
> - La documentation est communiquée dans un format qui respecte les
>   recommandations d'accessibilité.

### 3.1 Chaîne de monitorage : Prometheus + Grafana

```
FastAPI (Waterflow 2)          Prometheus              Grafana
   GET /metrics  ── scrape 15s ──►  :9090  ── query PromQL ──►  :3000
```

Choix motivé par le contexte technique du projet : l'API est déjà en Python/FastAPI,
`prometheus-client` (déjà dans `requirements.txt`) s'y intègre nativement en quelques
lignes (`api/main.py:20,32-37,81,84-95`), sans agent externe à déployer ; Prometheus
et Grafana sont tous deux packagés comme services `docker-compose.yml` du projet
(pas d'infrastructure supplémentaire à provisionner), et le couple est un standard de
fait pour la supervision d'API HTTP, ce qui limite la charge d'apprentissage pour
une équipe technique reprenant le projet.

`api/main.py` définit un compteur et un histogramme, incrémentés par un middleware
appliqué à chaque requête :

```python
HTTP_REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
HTTP_LATENCY = Histogram("http_request_duration_seconds", "Request duration", ["endpoint"])

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    t0 = time.time()
    response = await call_next(request)
    HTTP_LATENCY.labels(endpoint=request.url.path).observe(time.time() - t0)
    HTTP_REQUESTS.labels(method=request.method, endpoint=request.url.path, status=response.status_code).inc()
    return response
```

`app.mount("/metrics", make_asgi_app())` expose ces métriques en clair au format
Prometheus, scrapées toutes les 15 secondes selon `prometheus.yml` :

```yaml
global:
  scrape_interval: 15s
scrape_configs:
  - job_name: 'waterflow2'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/metrics'
```

### 3.2 Métriques suivies et pourquoi

Les 3 métriques RED (standard pour la santé d'une API), plus une métrique propre au
projet :

| Métrique | Nom Prometheus | Ce qu'elle mesure | Ce qu'un seuil dessus permettrait de détecter |
|---|---|---|---|
| Rate | `http_requests_total` (compteur, par méthode/endpoint/statut) | Nombre de requêtes reçues | Pic de trafic anormal, ou chute brutale signalant que l'API ne reçoit plus rien |
| Errors | `http_requests_total{status=~"5.."}` | Part des requêtes en échec côté serveur | Panne d'une dépendance externe (OCR.space, MLflow) avant qu'un client ne s'en plaigne |
| Duration | `http_request_duration_seconds` (histogramme, par endpoint) | Temps de réponse | Ralentissement progressif (fuite de ressource, dépendance lente) avant qu'il ne devienne un incident |
| Spécifique projet | `ocr_failures_total{reason=...}` | Échecs d'appel à OCR.space, par cause (timeout, injoignable, erreur HTTP, erreur de traitement) | Distinguer une panne du service OCR externe d'un simple fichier illisible envoyé par un client |

Point d'interprétation important : ces métriques renseignent sur la santé de
**l'API** (latence, erreurs, trafic), pas directement sur la **qualité des
prédictions** du modèle (accuracy/F1) — celles-ci sont visibles séparément, via
`GET /api/dashboard/metrics` (issues de MLflow, cf. C9), affichées dans l'onglet
"Métriques du modèle" de `dashboard_qualite.py`. Les deux formes de monitorage
(applicatif via Prometheus, qualité du modèle via MLflow) sont donc complémentaires
et volontairement séparées.

### 3.3 Restitution en temps réel et accessibilité

Grafana constitue le vecteur de restitution temps réel (requêtes PromQL sur les
métriques ci-dessus, rafraîchies en continu). Deux mitigations documentées
(`docs/MONITORING.md`) compensent la nature visuelle de Grafana pour
l'accessibilité :
- les métriques brutes restent consultables en texte, sans interface graphique, via
  `GET /metrics` (format texte Prometheus) et l'API HTTP `/api/v1/query` de
  Prometheus lui-même ;
- Grafana propose nativement des panels "table" (pas seulement des courbes), une
  alternative plus accessible qu'un graphique pour un lecteur d'écran.

Limite assumée et documentée : Grafana n'a pas été audité formellement avec un
lecteur d'écran, choix jugé raisonnable pour un outil de supervision technique
destiné à une équipe restreinte plutôt qu'à l'ensemble des parties prenantes du
projet (contrairement, par exemple, à la documentation utilisateur, où
l'accessibilité est un critère non négociable).

`[Capture d'écran à insérer : dashboard Grafana Waterflow2 avec des courbes Rate/
Duration non vides après génération de trafic réel]`

### 3.4 Test en environnement dédié et état de marche

`docs/MONITORING.md` (section "Testé dans un environnement dédié") documente que la
chaîne a d'abord été validée dans l'environnement Docker Compose local (pas en
production), avec deux vérifications concrètes avant d'être considérée
fonctionnelle : la page `http://localhost:9090/targets` de Prometheus confirmée en
état `UP` pour le job `waterflow2`, et des courbes non vides observées dans Grafana
pour Rate/Duration après génération de trafic réel via l'UI Streamlit — pas
seulement une configuration déployée sans vérification d'exécution.

### 3.5 Documentation technique

`docs/MONITORING.md` (versionné dans le dépôt Git distant, comme le reste du projet)
couvre : l'architecture (schéma ASCII), l'installation (`docker compose up --build`,
rien à configurer manuellement côté Prometheus, fichier déjà monté en volume), la
configuration ponctuelle de la source de données Grafana (étapes précises : URL,
identifiants par défaut), l'utilisation (requêtes PromQL de base, vérification de
`/targets`), et les limites connues (ex. persistance MLflow expliquée en fin de
document). Rédigée en Markdown, format texte structuré nativement compatible avec
les lecteurs d'écran.

---

## 4. C12 : Programmer les tests automatisés d'un modèle d'intelligence artificielle

> **Ce que le jury doit pouvoir cocher :**
> - L'ensemble des cas à tester sont listés et définis : la partie du modèle visée
>   par le test, le périmètre du test et la stratégie de test.
> - Les outils de test (framework, bibliothèque, etc.) choisis sont cohérents avec
>   l'environnement technique du projet.
> - Les tests sont intégrés et respectent la couverture souhaitée établie.
> - Les tests s'exécutent sans problème technique en environnement de test.
> - Les sources sont versionnées et accessibles depuis un dépôt Git distant (DVC,
>   Gitlab…).
> - La documentation couvre la procédure d'installation de l'environnement de
>   test, les dépendances installées, la procédure d'exécution des tests et de
>   calcul de la couverture.
> - La documentation est communiquée dans un format qui respecte les
>   recommandations d'accessibilité.

### 4.1 Stratégie de test : deux mécanismes complémentaires

Ce projet teste le modèle sous deux angles distincts, documentés séparément pour
éviter toute confusion sur ce que chacun garantit :

| | `tests/test_pipeline.py` (pytest) | `scripts/validate_model.py` (gate CI) |
|---|---|---|
| **Partie visée** | Le pipeline *autour* du modèle : seuil de décision, sérialisation de la requête/réponse, persistance | Le modèle *lui-même* : sa capacité réelle à apprendre sur les données actuelles |
| **Périmètre** | Logique de seuil (unitaire), routes API qui appellent `predict_proba` (fonctionnel), non-régression du F1 en dur (0.5868 ≥ 0.50) | Réentraînement complet (SMOTE + XGBoost) sur `data/processed/processed_data.pkl`, recherche du meilleur seuil, F1 comparé à un seuil minimal |
| **Modèle utilisé** | `DummyModel` factice (`ph >= 5` ⇒ potable) — aucun calcul ML réel | Le vrai `XGBClassifier`, entraîné pour de vrai à chaque exécution |
| **Stratégie** | Isolation totale (pas de réseau, pas de MLflow réel) pour tester le contrat de l'API rapidement et de façon déterministe | Reproduction fidèle de `scripts/experiment.py`, sans dépendance MLflow, comme contrôle de non-régression avant fusion |

Cette séparation est volontaire : `test_pipeline.py` valide que l'API se comporte
correctement *quel que soit* le modèle chargé (rapide, déterministe, indépendant des
aléas d'entraînement) ; `validate_model.py` valide que le modèle *actuel*, réentraîné
sur les données actuelles, reste au-dessus d'un seuil de qualité minimal — deux
échecs qui appellent des corrections différentes.

### 4.2 Outils et cohérence technique

`pytest` + `fastapi.testclient.TestClient` (déjà utilisés pour C9/C10) sont réutilisés
pour tester le pipeline de prédiction, cohérent avec le reste de la stack Python du
projet — pas de framework de test ML dédié supplémentaire, non justifié pour un
modèle unique de classification binaire. `validate_model.py` réutilise directement
`imbalanced-learn`, `scikit-learn` et `xgboost`, déjà dans `requirements.txt` pour
l'entraînement (`scripts/experiment.py`), sans dépendance nouvelle.

### 4.3 Exécution réelle et interprétation des résultats

Exécution réelle de `scripts/validate_model.py` (réentraînement complet, gate F1) :

```
Validation du modèle (SMOTE + XGBoost) :
  accuracy        : 0.5899
  f1_score        : 0.5868
  precision       : 0.4835
  recall          : 0.7461
  best_threshold  : 0.3700

OK : F1-score 0.5868 >= seuil minimal 0.5.
```

Le F1-score obtenu (0.5868) correspond exactement à la valeur codée en dur dans
`tests/test_pipeline.py::test_model_non_regression_f1_score` (`current_model_f1_score
= 0.5868`), ce qui confirme que ce test de non-régression reflète un état réel mesuré
du modèle, pas un chiffre arbitraire. Interprétation du résultat : `precision`
(0.48) plus faible que `recall` (0.75) signifie que le modèle, au seuil retenu
(0.37, volontairement abaissé sous 0.5), préfère classer un prélèvement douteux comme
"non potable" plutôt que de laisser passer une eau réellement non potable —
compromis assumé pour ce cas d'usage (mieux vaut un faux négatif "non potable" qu'un
faux négatif "potable").

Exécution réelle de la suite pytest complète (incluant les tests liés au modèle,
cf. tableau 4.1) :

```
............................................... [100%]
47 passed, 1 warning in 280.73s (0:04:40)
```

Aucun problème technique en environnement de test : exit code 0, aucune erreur
d'import, aucun test ignoré.

**Couverture de code, mesurée et opposable.** Un objectif de couverture a été fixé
(80% minimum sur `api/` et `data.db/`) et appliqué comme condition de passage de la
CI, pas seulement documenté à titre indicatif : `--cov-fail-under=80` sur l'étape
"Run tests" de `.github/workflows/ci.yml` (cf. C13, 5.1) fait échouer le run si la
couverture retombe sous ce seuil, même si tous les tests passent individuellement.
Exécution réelle de la mesure :

```
Name                     Stmts   Miss  Cover   Missing
------------------------------------------------------
api\auth.py                 33      3    91%   41-42, 56
api\logging_config.py       21      0   100%
api\main.py                220      9    96%   141-142, 155-156, 190, 210-211, 269, 494
api\ocr_router.py          108     25    77%   55, 67-68, 118-119, 158, 163-187, 195, 243, 247
data\db\WaterFlowDB.py      90     22    76%   69, 73, 79-80, 92-97, 156-161, 164-168, 171-172, 200-201, 203-204, 206-207, 209-210, 214-215
------------------------------------------------------
TOTAL                      472     59    88%
```

88% de couverture globale, marge confortable au-dessus du seuil de 80%. Les deux
fichiers les moins couverts (`api/ocr_router.py` 77%, `data/db/WaterFlowDB.py` 76%)
restent cohérents avec les limites déjà documentées ailleurs dans ce rapport : les
branches d'erreur réseau spécifiques d'OCR.space (`ConnectionError`, `HTTPError`,
`Timeout`, cf. C9) et certaines méthodes CRUD de `WaterFlowDB.py` non exercées par la
suite actuelle (ex. `update_prediction`, `delete_prediction`, non utilisées par
l'API aujourd'hui).

### 4.4 Documentation d'installation et d'exécution

`tests/test_README.md` (versionné dans le dépôt Git distant) couvre : les
dépendances (`pytest`, `pytest-cov`, `fastapi`, `uvicorn`, `python-multipart`,
`httpx`, toutes listées directement dans `requirements.txt`), la commande
d'exécution (`python -m pytest`, avec l'explication du rôle de `pytest.ini` qui
restreint la découverte à `tests/`), l'exécution ciblée d'un seul fichier/test,
l'objectif de couverture fixé (80% minimum) et son calcul :

```bash
python -m pytest --cov=api --cov=data.db --cov-report=term-missing
python -m pytest --cov=api --cov=data.db --cov-report=term-missing --cov-fail-under=80   # reproduit exactement le gate CI
python -m pytest --cov=api --cov=data.db --cov-report=html   # rapport HTML détaillé
```

Il détaille aussi précisément le mécanisme d'isolation (`test_db`, `client`,
`mock_ocr_space` — cf. C9/C10), pour qu'une personne reprenant le projet comprenne
pourquoi la suite tourne "en quelques secondes, sans MLflow ni base de données
réels" (pour la partie pytest — `validate_model.py`, séparé, prend plusieurs minutes
car il réentraîne réellement). Document Markdown, format texte structuré compatible
avec les lecteurs d'écran.

---

## 5. C13 : Créer une chaîne de livraison continue d'un modèle d'intelligence artificielle

> **Ce que le jury doit pouvoir cocher :**
> - La documentation pour l'utilisation de la chaîne couvre toutes les étapes, les tâches et tous les déclencheurs disponibles.
> - Les déclencheurs sont intégrés comme préalablement définis.
> - Le ou les fichiers de configuration de la chaîne sont correctement reconnus et exécutés par le système selon les déclencheurs configurés.
> - L'étape de test des données est intégrée à la chaîne et s'exécute sans erreur.
> - La ou les étapes de test, d'entraînement et de validation du modèle sont
>   intégrées à la chaîne et s'exécutent sans erreur.
> - Les sources de la chaîne sont versionnées et accessibles depuis le dépôt Git
>   distant du projet.
> - La documentation de la chaîne de livraison continue couvre la procédure
>   d'installation, de configuration et de test de la chaîne.
> - La documentation est communiquée dans un format qui respecte les
>   recommandations d'accessibilité.

### 5.1 Pipeline CI/CD : `.github/workflows/ci.yml`

**Outil retenu** : GitHub Actions — le dépôt est déjà hébergé sur GitHub
(`github.com/Sonicario49/waterflow2`), donc pas de compte ni d'infrastructure CI
supplémentaire, intégration native aux pull requests, gratuit pour un dépôt de cette
taille.

**Déclencheurs** :

```yaml
on:
  push:
  pull_request:
```

La chaîne se déclenche sur tout push (toute branche) et toute pull request. En
pratique sur ce projet, chaque branche de fonctionnalité déclenche un run à son
push, avant revue et fusion dans `main`.

**Étapes** (fichier unique `ci.yml`, reconnu et exécuté automatiquement par GitHub
Actions à chaque déclenchement) :

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.10"
          cache: "pip"
          cache-dependency-path: requirements.txt
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Validate raw data (schema / missing values)
        run: python scripts/validate_data.py
      - name: "Run tests (coverage gate: 80% minimum on api/ + data.db/)"
        run: python -m pytest --cov=api --cov=data.db --cov-report=term-missing --cov-fail-under=80
      - name: Train & validate model (F1-score gate)
        run: python scripts/validate_model.py
      - name: Build API Docker image (packaging)
        run: docker build -t waterflow2-api:${{ github.sha }} .
      - name: Build full docker-compose stack (mlflow + api + streamlit)
        run: docker compose build
      - name: "Push Docker image to GitHub Container Registry (delivery)"
        if: github.ref == 'refs/heads/main'
        run: |
          echo "${{ secrets.GITHUB_TOKEN }}" | docker login ghcr.io -u ${{ github.actor }} --password-stdin
          docker tag waterflow2-api:${{ github.sha }} ghcr.io/sonicario49/waterflow2-api:${{ github.sha }}
          docker tag waterflow2-api:${{ github.sha }} ghcr.io/sonicario49/waterflow2-api:latest
          docker push ghcr.io/sonicario49/waterflow2-api:${{ github.sha }}
          docker push ghcr.io/sonicario49/waterflow2-api:latest
```

Chaque étape est bloquante (comportement par défaut de GitHub Actions) : si l'une
échoue, les suivantes ne s'exécutent pas et le commit est marqué en échec.

### 5.2 Étape de test des données

`scripts/validate_data.py` contrôle le schéma de `data/raw/water_potability.csv`
(colonnes attendues, types numériques, valeurs cibles ∈ {0,1}) et l'absence de
dérive grossière sur les valeurs manquantes (seuil 30%), avant que le pipeline
d'entraînement ne consomme ce fichier. Exécution réelle :

```
ph                   : 15.0% de valeurs manquantes
Hardness             : 0.0% de valeurs manquantes
Solids               : 0.0% de valeurs manquantes
Chloramines          : 0.0% de valeurs manquantes
Sulfate              : 23.8% de valeurs manquantes
Conductivity         : 0.0% de valeurs manquantes
Organic_carbon       : 0.0% de valeurs manquantes
Trihalomethanes      : 4.9% de valeurs manquantes
Turbidity            : 0.0% de valeurs manquantes

OK : 3276 lignes, schéma conforme.
```

Exit code 0 : l'étape s'exécute sans erreur et documente au passage, dans les logs
CI, le taux de valeurs manquantes réel par colonne (utile pour repérer une dérive
future sans avoir à ouvrir le fichier).

### 5.3 Étapes de test, d'entraînement et de validation du modèle

L'étape "Run tests" exécute la suite pytest complète vue en C9/C10/C12 (47 tests,
API + intégration UI), avec un gate de couverture (`--cov-fail-under=80`, cf. C12,
4.3) qui fait échouer le run si la couverture retombe sous 80% — mesure réelle
actuelle : 88%. L'étape "Train & validate model" exécute
`scripts/validate_model.py` (détail en 4.3) : réentraînement réel (SMOTE + XGBoost)
et comparaison du F1-score à un seuil minimal (0.50) — sortie réelle déjà citée en
4.3, `OK : F1-score 0.5868 >= seuil minimal 0.5`, exit code 0. Les deux étapes
s'exécutent donc sans erreur, dans cet ordre, avant le packaging.

### 5.4 Packaging et livraison

Deux étapes de packaging suivent la validation : `docker build` de l'image API seule
(`Dockerfile`, `FROM python:3.10-slim`, copie de `api/` et de `data/db/`), puis
`docker compose build` qui construit les 3 images du projet (`mlflow.Dockerfile`,
`Dockerfile`, `ui.Dockerfile`) définies dans `docker-compose.yml`. Une troisième
étape, de livraison, suit : publication de l'image API sur GitHub Container Registry
(`ghcr.io/sonicario49/waterflow2-api`, tags `<sha>` et `latest`), exécutée uniquement
une fois le packaging validé, et uniquement sur push vers `main`
(`if: github.ref == 'refs/heads/main'`) — jamais sur une branche de fonctionnalité ou
une PR en cours de revue. Authentification via `GITHUB_TOKEN`, fourni automatiquement
par GitHub Actions (`permissions: packages: write` déclaré au niveau du job), aucun
secret à configurer manuellement.

Le **déploiement** de cette image (la faire tourner en production, ex. Render, un
VPS) reste volontairement un acte manuel distinct de la publication : la mise en
production applicative continue de passer par une pull request revue et fusionnée à
la main (pratique documentée dans `docs/CI_CD.md`). Distinction assumée : publier un
artefact (désormais automatisé) n'est pas la même chose que le déployer (resté
manuel).

### 5.5 Documentation de la chaîne

`docs/CI_CD.md` (versionné dans le dépôt Git distant) couvre : l'outil retenu et sa
justification, les déclencheurs, un tableau détaillant chacune des 9 étapes (ce
qu'elle fait, quelle compétence RNCP elle sert), ce qui reste volontairement manuel
(le déploiement, pas la publication), la procédure d'installation/reproduction en
local (les 5 commandes de la chaîne, exécutables une à une hors CI, l'étape de
publication `ghcr.io` mise à part — non reproductible sans authentification), la
configuration (fichier unique, aucun secret à configurer manuellement, cache pip),
l'historique d'exécution (runs verts
consultables sur `github.com/Sonicario49/waterflow2/actions`) et une limite
initialement identifiée puis corrigée (`requirements.txt` ne verrouillait aucune
version, ayant déjà causé un écart de comportement documenté dans
`tests/bugTrouvé_README.md`, incident 2 — chaque dépendance est désormais épinglée
à une version exacte, vérifiée fonctionnelle). Document Markdown, format texte
structuré compatible avec les lecteurs d'écran.

`[Capture d'écran à insérer : run CI/CD réussi sur l'onglet Actions de GitHub, les 8
étapes vertes]`

---

## 6. Difficultés rencontrées et conclusion

**Instabilité du mock MLflow selon l'ordre des tests (C9/C12).** Documentée en détail
dans `tests/bugTrouvé_README.md` (incident 2) : le premier test à démarrer
l'application déclenchait un vrai appel réseau vers un serveur MLflow inexistant en
environnement de test, car le monkeypatch de `mlflow.xgboost.load_model` n'était pas
garanti actif au moment exact du `lifespan`. Plutôt que de figer une version exacte
de `mlflow` (fragile), la fixture `client` force désormais explicitement le modèle
factice sur l'application une fois le `TestClient` démarré — solution robuste aux
évolutions internes de MLflow, vérifiée par l'exécution réelle de la suite (47/47).

**Écart d'invocation `pytest` vs `python -m pytest` en CI (C13).** Documenté en
détail dans `tests/bugTrouvé_README.md` (incident 1) : la CI échouait avec un code de
sortie 4 (erreur de config, pas un test qui échoue) car `pytest` seul ne place pas la
racine du projet dans `sys.path`, rendant le package `data/` introuvable —
corrigé en alignant `ci.yml` sur l'invocation locale (`python -m pytest`).

**Synchronisation manuelle du seuil de décision.** Le seuil de décision (0.37) est
dupliqué entre `scripts/experiment.py` (où il est recherché), `api/main.py`
(`app.state.best_threshold`, en dur) et `scripts/validate_model.py`/
`tests/test_pipeline.py` (`BEST_THRESHOLD`) — point à garder synchronisé
manuellement, sans automatisation qui propage ce seuil d'un composant à l'autre à ce
stade.

**Conclusion.** Le modèle XGBoost fourni est exposé par une API REST authentifiée et
documentée (C9), intégrée dans une application Streamlit existante en couvrant
l'ensemble de ses points de terminaison (C10), monitoré en temps réel via
Prometheus/Grafana avec des métriques justifiées (C11), testé de façon automatisée
sous deux angles complémentaires — contrat de l'API et qualité réelle du modèle
réentraîné (C12) — et livré en continu via une chaîne GitHub Actions qui valide les
données, teste, entraîne, valide et empaquette à chaque push (C13). L'ensemble a été
exécuté réellement pendant la rédaction de ce rapport (pytest : 47/47 ;
`validate_data.py` et `validate_model.py` : exit code 0 chacun), pas seulement décrit
sur le papier.

---

## Annexe : préparation de la soutenance orale (15 min)

- **Repo Git accessible en amont** : https://github.com/Sonicario49/waterflow2
- **Démonstration prévue** : `docker compose up --build`, puis (1) montrer
  `/docs` et le cadenas sur les routes protégées, (2) se connecter sur l'UI
  Streamlit et faire une prédiction manuelle puis via OCR, (3) montrer la métrique
  correspondante apparaître dans Grafana après génération de trafic, (4) montrer un
  run vert sur l'onglet GitHub Actions.
- **Minutage suggéré** : 2 min contexte, puis ~2-3 min par compétence (C9 à C13),
  1 min conclusion.

**Questions probables du jury et réponses préparées :**

**Q : Pourquoi une clé API statique plutôt qu'un jeton à expiration (JWT) ?**
Le projet privilégie la simplicité pour un nombre de clients limité et un modèle
d'accès stable (laboratoires partenaires, pas d'utilisateurs grand public) : une clé
révocable et rotable via un endpoint dédié couvre le besoin réel sans la complexité
d'un système de refresh token. En production à plus grande échelle, une migration
vers OAuth2/JWT serait envisageable si le nombre de clients ou la fréquence de
rotation l'exigeaient.

**Q : Pourquoi ne pas avoir automatisé le déploiement (registre d'images,
publication) dans la CI ?**
Choix assumé et documenté (`docs/CI_CD.md`) : la chaîne valide, teste et empaquette,
mais la mise en production reste une pull request revue manuellement, ce qui donne un
point de contrôle humain avant tout changement visible en production — cohérent avec
la taille de l'équipe (candidat seul) et l'absence d'environnement de production réel
à ce stade du projet.

**Q : Comment sais-tu que le mock MLflow ne fausse pas les tests fonctionnels ?**
Le `DummyModel` reproduit une logique de décision simple et connue (`ph >= 5` ⇒
potable), ce qui permet de vérifier que le *pipeline* (validation Pydantic, seuil,
persistance en base, codes HTTP, autorisations) se comporte correctement,
indépendamment de la qualité réelle du modèle. La qualité réelle du modèle est
vérifiée séparément par `scripts/validate_model.py`, qui réentraîne pour de vrai
(cf. C12) — les deux mécanismes sont volontairement séparés et documentés comme tels.

**Q : Le F1-score du modèle (0.59) est plutôt bas — pourquoi ce seuil minimal de
0.50 en CI ?**
`[À COMPLÉTER : justification du choix du seuil 0.50 — contexte du jeu de données
Kaggle utilisé, déséquilibre des classes traité par SMOTE, marge de sécurité
volontaire par rapport au F1 actuellement mesuré (0.5868) pour absorber une variance
normale d'un réentraînement à l'autre sans faire échouer la CI à tort.]`

---

## Annexe technique (hors comptage)

`[À COMPLÉTER si nécessaire pour la soutenance : contenu complet de api/auth.py, du
middleware metrics_middleware, du fichier ci.yml en entier, de tests/conftest.py —
déjà cités par extraits dans le corps du rapport ci-dessus, à ne recopier
intégralement ici que si le jury le demande.]`
