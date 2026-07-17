# Diagramme de flux de données - Waterflow 2

Diagramme de flux de données (DFD) de la stack applicative, dérivé de `docker-compose.yml`
et des appels HTTP réels entre composants (`ui.py`/`views/*.py` → `api/*.py` → `data/db/WaterFlowDB.py`
/ MLflow / OCR.space). Sert de preuve pour C15. Distinct de `docs/parcours_utilisateurs.md`, qui
documente les parcours utilisateurs (écrans, boutons) : ce document-ci documente les flux de
données entre composants système (client, applications, bases, services externes).

Pour visualiser : coller le bloc dans [mermaid.live](https://mermaid.live), ou l'extension
"Markdown Preview Mermaid Support" dans VS Code.

## Vue d'ensemble

```mermaid
flowchart LR
    User([Utilisateur<br/>navigateur])

    subgraph Docker["Stack Docker Compose"]
        UI[Streamlit UI<br/>:8501]
        API[API FastAPI<br/>:8000]
        DB[(SQLite<br/>data/db/waterflow.db)]
        ML[(MLflow<br/>registre + tracking<br/>:5000)]
        Prom[Prometheus<br/>:9090]
        Graf[Grafana<br/>:3000]
    end

    OCR[[OCR.space<br/>API externe SaaS]]

    User -->|clé API, 9 mesures,<br/>fichier labo image/PDF| UI
    UI -->|HTTP + header X-API-Key<br/>login, measurements,<br/>ocr/lab-report, clients,<br/>dashboard/*, me| API
    API -->|réponse JSON<br/>prédiction / erreur| UI
    UI -->|affichage résultat,<br/>historique, dashboards| User

    API -->|SELECT / INSERT / UPDATE / DELETE<br/>users, prediction, audit_logs| DB
    DB -->|lignes retournées| API

    API -->|chargement modèle Production<br/>au démarrage app.state.model,<br/>lecture métriques/versions| ML
    ML -->|modèle sérialisé,<br/>métriques, paramètres| API

    API -->|upload fichier image/PDF| OCR
    OCR -->|texte brut extrait| API

    Prom -->|scrape GET /metrics<br/>toutes les 15s| API
    Graf -->|requêtes PromQL| Prom
```

## Flux hors application (entraînement, hors requête live)

```mermaid
flowchart LR
    CSV[(data/raw/<br/>water_potability.csv)]
    Script[scripts/experiment.py]
    ML[(MLflow<br/>registre + tracking)]

    CSV -->|lecture, split train/val| Script
    Script -->|log params/metrics/model,<br/>promotion en Production| ML
```

## Nature des données par flux, au regard du RGPD

| Flux | Donnée transportée | Personnelle ? |
|---|---|---|
| Utilisateur → UI → API | Clé API (identifiant d'authentification) | Oui — assimilable à un identifiant de compte |
| API → DB (`users`) | `username`, hash SHA-256 de la clé | Oui — nom d'utilisateur, jamais la clé en clair |
| API → DB (`prediction`) | 9 mesures physico-chimiques, résultat, `user_id` | Mesures non personnelles ; `user_id` relie la mesure à un compte |
| API → DB (`audit_logs`) | Endpoint, méthode, IP, `user_id` | IP + `user_id` — anonymisé (`user_id = NULL`) à la suppression du compte (droit à l'oubli, `DELETE /api/me`) |
| API → OCR.space | Contenu binaire du fichier labo | Potentiellement — dépend du contenu réel de la fiche (nom du laboratoire, etc.), voir limite documentée sur `ocr_raw_text` |
| API → MLflow | Aucune donnée personnelle (modèle, métriques agrégées) | Non |
| API → Prometheus | Métriques agrégées (compteurs, histogrammes) | Non |

Le seul flux sortant vers un tiers externe est `API → OCR.space` (upload du fichier labo) — c'est
la seule donnée du projet qui quitte l'infrastructure auto-hébergée (Docker Compose local),
raison pour laquelle `api/ocr_router.py` ne transmet jamais le `client_id` dans cet appel :
l'identité du client reste dans l'infrastructure interne, seul le contenu du document part vers
OCR.space.
