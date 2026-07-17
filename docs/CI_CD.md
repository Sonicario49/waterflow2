# CI/CD — Waterflow 2

Ce document couvre la chaîne d'intégration et de livraison continues du projet
(`.github/workflows/ci.yml`), pour le modèle IA (entraînement/validation) comme pour
l'application (tests, packaging). Il sert de preuve pour C13, C18 et C19 : les trois
compétences portent sur la même chaîne, vue sous des angles différents (modèle / application /
livraison).

## Outil retenu

**GitHub Actions**, choisi car le dépôt est déjà hébergé sur GitHub (`github.com/Sonicario49/waterflow2`)
— pas de compte ou d'infrastructure CI supplémentaire à gérer, intégration native aux pull
requests, et gratuit pour un dépôt de cette taille.

## Déclencheurs

Définis dans `ci.yml` :
```yaml
on:
  push:
  pull_request:
```
La chaîne se déclenche sur **tout push** (toute branche) et **toute pull request**. En pratique
sur ce projet : chaque branche de fonctionnalité déclenche un run à son push, avant la revue et
la fusion dans `main`.

## Étapes de la chaîne

| # | Étape | Ce qu'elle fait | Concerne |
|---|---|---|---|
| 1 | `Checkout` | Récupère le code du commit déclencheur | C18 |
| 2 | `Set up Python` | Installe Python 3.10, active le cache pip (`requirements.txt`) | C18 |
| 3 | `Install dependencies` | `pip install -r requirements.txt` | C18 |
| 4 | `Validate raw data` | `python scripts/validate_data.py` — vérifie le schéma et l'absence de dérive sur `data/raw/water_potability.csv` | C13 |
| 5 | `Run tests` | `python -m pytest` — 47 tests (API + intégration UI) | C18 |
| 6 | `Train & validate model` | `python scripts/validate_model.py` — réentraîne (SMOTE + XGBoost) et vérifie le F1-score contre un seuil minimal (gate qualité) | C13 |
| 7 | `Build API Docker image` | `docker build -t waterflow2-api:<sha> .` — packaging de l'API | C19 |
| 8 | `Build MLflow Docker image` | `docker build -f mlflow.Dockerfile -t waterflow2-mlflow:<sha> .` — packaging du service MLflow | C19 |
| 9 | `Build Streamlit Docker image` | `docker build -f ui.Dockerfile -t waterflow2-streamlit:<sha> .` — packaging de l'UI | C19 |
| 10 | `Build full docker-compose stack` | `docker compose build` — reconstruit les 3 images via `docker-compose.yml`, validation croisée de la configuration compose elle-même | C19 |
| 11 | `Push Docker images to GitHub Container Registry` | `docker push ghcr.io/sonicario49/waterflow2-{api,mlflow,streamlit}:<sha>` + `:latest` — étape de **livraison**, exécutée uniquement une fois les étapes de packaging (7-10) validées, et uniquement sur `main` (`if: github.ref == 'refs/heads/main'`), pas sur chaque branche/PR | C19 |

Chaque étape est bloquante : si l'une échoue, les suivantes ne s'exécutent pas (comportement par
défaut de GitHub Actions), et le commit est marqué en échec sur GitHub.

## Ce qui reste manuel (volontairement laissé ouvert)

La chaîne livre désormais automatiquement les 3 images construites sur un registre (étape 11,
`ghcr.io/sonicario49/waterflow2-{api,mlflow,streamlit}`) — de quoi redéployer la stack complète,
pas seulement l'API. Le **déploiement** de ces images (les faire tourner quelque part en
production, ex. Render, un VPS, un cluster) reste un acte manuel distinct : la mise en
production applicative continue de passer par une pull request revue et mergée à la main (10+
PR mergées ainsi sur ce projet, voir l'historique GitHub) plutôt que par un déclencheur
automatique de déploiement. Distinction assumée : *publier* des artefacts (automatisé) ≠ les
*déployer* en production (manuel).

## Installation / reproduction en local

1. Cloner le dépôt et se placer à sa racine.
2. `pip install -r requirements.txt`
3. Lancer individuellement les étapes de la chaîne, dans l'ordre :
   ```bash
   python scripts/validate_data.py
   python -m pytest
   python scripts/validate_model.py
   docker build -t waterflow2-api:local .
   docker build -f mlflow.Dockerfile -t waterflow2-mlflow:local .
   docker build -f ui.Dockerfile -t waterflow2-streamlit:local .
   docker compose build
   ```
   L'étape 11 (`docker push` vers `ghcr.io`) n'est pas reproductible telle quelle en local sans
   authentification à GitHub Container Registry (`docker login ghcr.io`) — en CI, elle utilise le
   `GITHUB_TOKEN` fourni automatiquement par GitHub Actions, jamais un secret à configurer
   manuellement.

## Configuration

- Fichier unique : `.github/workflows/ci.yml`, versionné avec le reste du code.
- Aucun secret externe à configurer manuellement : l'étape de publication sur `ghcr.io` utilise
  le `GITHUB_TOKEN` fourni automatiquement par GitHub Actions à chaque run (`permissions:
  packages: write` déclaré au niveau du job), pas un token créé/stocké à la main.
- Le cache pip (`cache: "pip"`, `cache-dependency-path: requirements.txt`) accélère les runs
  suivants tant que `requirements.txt` ne change pas.

## Historique d'exécution

Chaque push/PR sur ce projet a déclenché un run visible dans l'onglet **Actions** du dépôt
(`github.com/Sonicario49/waterflow2/actions`). Les runs précédents (avant l'ajout des étapes de
publication) sont verts de bout en bout, y compris les étapes de build Docker — les étapes de
build MLflow/Streamlit et de publication sur `ghcr.io` (3 images) sont nouvelles, à confirmer
vertes sur le prochain push vers `main`. Vérifié en local avant publication (`docker build`
réussi pour `mlflow.Dockerfile` et `ui.Dockerfile`, images supprimées ensuite).

## Limite corrigée

`requirements.txt` ne fixait initialement aucune version de dépendance — un run pouvait donc
installer des versions plus récentes qu'un run précédent, ce qui avait déjà causé un écart de
comportement observé entre environnements (voir `tests/bugTrouvé_README.md`, incident 2).
Chaque dépendance est désormais épinglée à une version exacte (`==`), verrouillée sur les
versions vérifiées fonctionnelles (47/47 tests, couverture 88%) : un `pip install -r
requirements.txt` installe systématiquement le même jeu de versions, quel que soit
l'environnement ou la date d'exécution.
