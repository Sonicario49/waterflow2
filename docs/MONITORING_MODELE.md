# Monitorage du modèle — Waterflow 2

Chaîne de supervision **du modèle** : les métriques de performance (F1, accuracy, precision,
recall) loggées dans MLflow pour chaque version entraînée sont exposées en temps réel via l'API
et restituées dans le Dashboard Qualité. Sert de preuve pour C11. À ne pas confondre avec
`docs/monitoring_systeme.md` (preuve pour C20, cf. Rapport E5) qui supervise la **santé de
l'application** (erreurs, latence, trafic) via Prometheus/Grafana — les deux s'appuient sur des
outils différents, pour des questions différentes.

## Architecture

```
MLflow Model Registry          API FastAPI                    Dashboard Qualité (Streamlit)
  (metrics par run_id)  ──►  GET /api/dashboard/metrics   ──►  onglet "Métriques du modèle"
                         ──►  GET /api/dashboard/model-versions ──► onglet "Comparaison des versions"
                         ──►  POST /api/dashboard/replay   ──►  formulaire de rejeu
```

MLflow est déjà la brique de tracking/registre utilisée pour l'entraînement et le chargement du
modèle en production (cf. C9, C13) — la réutiliser comme source des métriques de monitorage évite
d'introduire un second outil (ex. un tracker de métriques ML dédié) pour un besoin qu'elle couvre
déjà nativement (`MlflowClient().get_run(run_id).data.metrics`).

## Métriques exposées (expliquées)

| Métrique | Ce qu'elle mesure | Interprétation pour ce projet |
|---|---|---|
| `accuracy` | Proportion globale de prédictions correctes | Trompeuse seule sur un jeu déséquilibré — gardée à titre indicatif, jamais comme seul critère de décision |
| `f1_score` | Moyenne harmonique precision/recall | Métrique de référence retenue (cf. `scripts/experiment.py`, seuil balayé 0.30-0.70 pour la maximiser) |
| `precision` | Part des prédictions "potable" réellement potables | Plus faible que le recall à ce seuil (0.48) : compromis quantifié, piste d'amélioration chiffrée à 0.50 déjà identifiée (cf. Rapport E3 C12) |
| `recall` | Part des eaux réellement potables correctement identifiées | Plus élevé que la precision (0.75), conséquence directe du seuil retenu |
| `best_threshold` | Seuil de décision retenu sur `predict_proba` | 0.37, issu d'un balayage qui maximise le F1 (cf. `scripts/experiment.py`) |

Exécution réelle (`GET /api/dashboard/metrics`, version `Production` courante) :

```json
{
  "version": "2",
  "run_id": "0967ba09f96c420c9279d95203883ff8",
  "stage": "Production",
  "metrics": {
    "accuracy": 0.5899390243902439,
    "f1_score": 0.5867895545314901,
    "precision": 0.4835443037974684,
    "recall": 0.74609375,
    "best_threshold": 0.37000000000000005
  }
}
```

## Vecteur de restitution en temps réel

`dashboard_qualite.py`, deux onglets dédiés (accessibles aux rôles `Quality_Analyst`/`Admin`) :

- **"Métriques du modèle"** : une carte (`st.metric`) par métrique de la version `Production`
  courante, plus un menu déroulant listant les hyperparamètres. Chaque appel de l'onglet
  interroge `GET /api/dashboard/metrics` en direct — pas une valeur figée à la construction du
  dashboard.
- **"Comparaison des versions"** : tableau (`st.dataframe`) listant toutes les versions
  enregistrées avec leurs métriques (`GET /api/dashboard/model-versions`), et un formulaire de
  rejeu qui charge une version précise du modèle (`runs:/<run_id>/model`) pour la comparer sur le
  même prélèvement (`POST /api/dashboard/replay`).

## Accessibilité de l'outil de restitution

Contrairement à Grafana (interface exclusivement graphique, cf. `docs/monitoring_systeme.md`),
le vecteur de restitution ici est un dashboard Streamlit dont l'accessibilité est un critère
d'acceptation documenté dès la conception (`docs/user_stories.md`, US-07/US-08, cf. C14) :

- **WCAG 1.3.1 (Information et relations)** : chaque carte de métrique expose son libellé et sa
  valeur comme une paire associée pour un lecteur d'écran, pas deux blocs de texte juxtaposés
  visuellement.
- **WCAG 1.4.3 (Contraste minimum)** : texte des métriques/paramètres ≥ 4.5:1.
- **WCAG 2.4.3 (Ordre de focus)** et **2.1.1 (Clavier)** : le sélecteur de version, les 9 champs
  de mesure et le bouton de rejeu suivent l'ordre visuel logique et sont opérables sans souris.

Limite assumée : ces critères sont des objectifs d'acceptation formulés dès la conception (cf.
C14, 1.4), pas un audit outillé réalisé (contraste mesuré, navigation lecteur d'écran de bout en
bout) — même limite que le reste de l'application Streamlit, pas spécifique à ce dashboard.

## Seuil d'alerte sur les métriques du modèle

`scripts/validate_model.py` (`MIN_F1_SCORE = 0.50`) réentraîne le modèle et recalcule son F1 à
chaque exécution CI (cf. C13) ; si le F1 recalculé tombe sous ce seuil, la chaîne échoue et
bloque la fusion — un seuil d'alerte réel sur une métrique du modèle, appliqué automatiquement
avant toute promotion, plutôt qu'une notification passive sur un dashboard qui resterait
consultée manuellement.

## Testé dans un environnement dédié

`tests/test_pipeline.py::test_dashboard_metrics`, `test_dashboard_model_versions`,
`test_dashboard_replay` exercent les 3 routes contre un `FakeMlflowClient` (`tests/conftest.py`)
— un double de test qui renvoie des versions/métriques déterministes, sans jamais appeler un
vrai serveur MLflow. La chaîne est donc validée dans un bac à sable avant d'être vérifiée en
conditions réelles (section suivante).

## Installation et configuration

Fait partie de `docker-compose.yml`, aucune configuration additionnelle : le service `mlflow`
démarre avec les autres (`docker compose up --build`), et l'API s'y connecte via
`MLFLOW_TRACKING_URI` (déjà documenté en C9/C15).

## Sources

Code et documentation versionnés sur le dépôt Git distant du projet
(`github.com/Sonicario49/waterflow2`), au même titre que le reste.
