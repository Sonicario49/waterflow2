# Waterflow 2

Plateforme MLOps qui prédit la potabilité de l'eau (potable/non potable) à partir de 9 mesures
physico-chimiques (ph, hardness, solids, chloramines, sulfate, conductivity, organic_carbon,
trihalomethanes, turbidity), à l'aide d'un modèle XGBoost tracké et servi via le Model Registry
de MLflow. Expose une API REST (FastAPI), une interface Streamlit, et une ingestion OCR de
fiches labo (image/PDF).

## Prérequis

- Python 3.10
- Docker + Docker Compose (pour l'option A ci-dessous)

## Installation

```bash
git clone https://github.com/Sonicario49/waterflow2.git
cd waterflow2
pip install -r requirements.txt
```

Toutes les dépendances sont épinglées à une version exacte dans `requirements.txt` — une
installation stricte donne systématiquement le même environnement, quel que soit le poste.

## Lancer le projet

### Option A — Docker Compose (recommandé, tous les services orchestrés ensemble)

```bash
docker compose up --build
```

Démarre 5 services : `mlflow` (:5000), `api` (:8000), `streamlit` (:8501), `prometheus` (:9090)
et `grafana` (:3000). Le service `mlflow` persiste son registre/artefacts dans `./mlflow_data`
(bind-mount) — sans ce volume, tout serait perdu à chaque rebuild du conteneur.

Sur un `mlflow_data/` neuf (premier lancement, ou après suppression), le registre de modèles
est vide et `/api/measurements` renvoie `503` tant qu'un modèle n'a pas été entraîné et promu :

```bash
python scripts/experiment.py   # pointe vers http://127.0.0.1:5000, mappé depuis le conteneur mlflow
docker compose restart api     # recharge le modèle "Production" nouvellement enregistré
```

### Option B — lancer les services individuellement (sans Docker)

```bash
# 1. Serveur de tracking + registre de modèles MLflow (UI sur http://127.0.0.1:5000)
python -m mlflow server --host 127.0.0.1 --port 5000

# 2. API FastAPI (charge le stage "Production" de water_quality_model depuis MLflow au démarrage)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Interface Streamlit (http://localhost:8501), interroge l'API sur 127.0.0.1:8000
python -m streamlit run ui.py
```

`waterflow2.bat` exécute ces 3 commandes dans l'ordre, sous Windows.

### Premier démarrage : créer la première clé Admin

```bash
python scripts/init_admin.py
```

Affiche la clé en clair **une seule fois** — elle n'est ensuite conservée en base que sous
forme de hash SHA-256.

### Entraîner une nouvelle version du modèle

```bash
python scripts/experiment.py
```

Charge `data/processed/processed_data.pkl`, applique SMOTE, entraîne un XGBoost, logue
paramètres/métriques/modèle dans MLflow, l'enregistre sous `water_quality_model` et promeut la
version la plus récente au stage `Production` — effectif dès le prochain (re)chargement du
modèle par l'API.

## Architecture

| Composant | Rôle |
|---|---|
| `api/main.py` + `api/auth.py` + `api/ocr_router.py` | API FastAPI : prédiction, gestion des clients, RGPD, dashboard qualité, ingestion OCR — authentification par clé API (header `X-API-Key`, hachée SHA-256), rôles `Client`/`Quality_Analyst`/`Admin` |
| `data/db/WaterFlowDB.py` | Couche d'accès unique à la base SQLite (`data/db/waterflow.db`, gitignorée) |
| `ui.py` + `views/` + `dashboard_qualite.py` | Interface Streamlit multi-pages, routage dynamique selon le rôle |
| `scripts/` | Entraînement (`experiment.py`), gates CI (`validate_data.py`, `validate_model.py`), setup (`init_admin.py`) |
| `.github/workflows/ci.yml` | Chaîne CI/CD (validation données → tests → entraînement/validation modèle → packaging Docker) |
| `prometheus.yml` + `docker-compose.yml` | Monitoring applicatif (Prometheus + Grafana) |

Documentation détaillée :
- [`docs/diagramme_flux_donnees.md`](docs/diagramme_flux_donnees.md) — flux de données entre composants
- [`docs/parcours_utilisateurs.md`](docs/parcours_utilisateurs.md) — parcours utilisateurs par rôle
- [`docs/user_stories.md`](docs/user_stories.md) — spécifications fonctionnelles + critères d'accessibilité WCAG
- [`docs/CI_CD.md`](docs/CI_CD.md) — chaîne d'intégration/livraison continues
- [`docs/MONITORING.md`](docs/MONITORING.md) — supervision Prometheus/Grafana
- [`docs/veille_mlflow.md`](docs/veille_mlflow.md) — veille technologique sur MLflow

## Tester l'API manuellement

```bash
# Prédiction manuelle
curl -X POST http://127.0.0.1:8000/api/measurements \
  -H "X-API-Key: <VOTRE_CLE_API>" -H "Content-Type: application/json" \
  -d "{\"features\": [7.2, 200.5, 15000, 8.1, 320, 450, 15.2, 65.4, 3.5]}"

# Historique
curl -X GET http://127.0.0.1:8000/api/measurements -H "X-API-Key: <VOTRE_CLE_API>"

# Ingestion OCR d'une fiche labo
curl -X POST http://127.0.0.1:8000/api/ocr/lab-report \
  -H "X-API-Key: <VOTRE_CLE_API>" -F "file=@test_OCR.png"

# Droit d'accès RGPD
curl -X GET http://127.0.0.1:8000/api/me -H "X-API-Key: <VOTRE_CLE_API>"

# Création d'un client (Admin uniquement)
curl -X POST http://127.0.0.1:8000/api/clients \
  -H "X-API-Key: <VOTRE_CLE_API_ADMIN>" -H "Content-Type: application/json" \
  -d "{\"username\": \"Laboratoire_Sud\", \"role\": \"Client\"}"
```

La documentation interactive complète (Swagger) est disponible sur `http://localhost:8000/docs`
une fois l'API démarrée.

## Tests

```bash
pytest
```

Voir [`tests/test_README.md`](tests/test_README.md) pour l'installation de l'environnement de
test, l'exécution ciblée et le calcul de couverture (objectif : 80% minimum sur `api/` et
`data.db/`, appliqué en CI).
