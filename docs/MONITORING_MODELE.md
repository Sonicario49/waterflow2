# Monitorage du modèle — Waterflow 2

Chaîne de supervision **du modèle** : les métriques de performance (F0.5, F1, accuracy,
precision, recall) loggées dans MLflow pour chaque version entraînée sont exposées en temps réel via l'API
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
| `f0.5_score` | Moyenne harmonique pondérée precision/recall (poids 0.8/0.2) | **Métrique de référence retenue** : la precision compte 4x plus que le recall, cohérent avec la priorité de minimiser les faux positifs "potable" (cf. Rapport E3 C12) |
| `f1_score` | Moyenne harmonique precision/recall (poids égaux) | Gardée à titre indicatif seulement — ne reflète plus le critère de décision réel depuis le passage au F0.5 |
| `precision` | Part des prédictions "potable" réellement potables | Volontairement priorisée sur le recall à ce seuil (0.67) — issue directement du choix F0.5 |
| `recall` | Part des eaux réellement potables correctement identifiées | Plus faible que la precision (0.36), conséquence assumée du seuil retenu |
| `best_threshold` | Seuil de décision retenu sur `predict_proba` | 0.58, issu d'une recherche aléatoire d'hyperparamètres qui maximise le F0.5 (cf. `scripts/tune_hyperparameters.py`, `scripts/experiment.py`) |

Exécution réelle (`GET /api/dashboard/metrics`, version `Production` courante) :

```json
{
  "version": "5",
  "run_id": "c47aaf3c2887498da160a4c05d3add4b",
  "stage": "Production",
  "metrics": {
    "accuracy": 0.6829268292682927,
    "f1_score": 0.4720812182741117,
    "f0.5_score": 0.5754950495049505,
    "precision": 0.6739130434782609,
    "recall": 0.36328125,
    "best_threshold": 0.58
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

`scripts/validate_model.py` (`MIN_F05_SCORE = 0.50`) réentraîne le modèle et recalcule son F0.5 à
chaque exécution CI (cf. C13) ; si le F0.5 recalculé tombe sous ce seuil, la chaîne échoue et
bloque la fusion — un seuil d'alerte réel sur une métrique du modèle, appliqué automatiquement
avant toute promotion, plutôt qu'une notification passive sur un dashboard qui resterait
consultée manuellement. Le gate a été délibérément changé de F1 vers F0.5 pour rester cohérent
avec la métrique de référence réellement utilisée (cf. tableau ci-dessus).

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
