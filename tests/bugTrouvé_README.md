# Bugs trouvés et interprétation des résultats de tests — Waterflow 2

Ce document trace deux incidents réels rencontrés sur la chaîne CI (`.github/workflows/ci.yml`),
diagnostiqués et corrigés sur la branche `fix-ci-pytest`. Objectif : montrer que les résultats de
tests (pass/fail, codes de sortie, logs) ont été lus et interprétés, pas seulement constatés.

---

## Incident 1 — `ModuleNotFoundError: No module named 'data'`

**Constat** : en local, `python -m pytest` donnait 32/32 tests passés. Sur GitHub Actions, la
même suite échouait avant même l'exécution d'un seul test, avec un code de sortie **4** (erreur
d'usage/config pytest — à distinguer d'un code **1**, qui signale des tests qui échouent
réellement).

**Log observé** :
```
ImportError while loading conftest '/home/runner/work/waterflow2/waterflow2/tests/conftest.py'.
tests/conftest.py:18: in <module>
    from data.db.WaterFlowDB import WaterFlowDB
E   ModuleNotFoundError: No module named 'data'
Error: Process completed with exit code 4.
```

**Diagnostic** : `ci.yml` lançait `pytest` (sans `python -m`). Contrairement à `python -m pytest`,
qui ajoute automatiquement le répertoire courant à `sys.path`, un simple `pytest` s'appuie sur son
propre mécanisme d'insertion de chemin. Comme `tests/` ne contient pas de `__init__.py`, pytest
insère `tests/` lui-même dans `sys.path` plutôt que la racine du projet — le package `data/`, qui
vit à la racine, devient donc introuvable. En local le bug était invisible car `python -m pytest`
masque ce problème.

**Correction** : `.github/workflows/ci.yml` — remplacement de `run: pytest` par
`run: python -m pytest` (commit `36a3b6b`, "fix ci yml"), pour aligner l'invocation CI sur celle
utilisée en local.

---

## Incident 2 — `test_health_endpoint` échoue avec `model_loaded: False`

**Constat** : une fois l'incident 1 corrigé, la CI passait à 31 tests réussis / 1 échoué. Le seul
test en échec, `test_health_endpoint`, est le premier test de la suite à utiliser la fixture
`client` (donc le premier à déclencher le chargement du modèle MLflow).

**Log observé** :
```
assert json_data["model_loaded"] is True
E       assert False is True
---------------------------- Captured stdout setup -----------------------------
Erreur chargement modèle : API request to http://127.0.0.1:5000/api/2.0/mlflow/registered-models/get-latest-versions failed
with exception HTTPConnectionPool(host='127.0.0.1', port=5000): Max retries exceeded ...
```

**Diagnostic** : le test tentait réellement de contacter un serveur MLflow sur `127.0.0.1:5000`,
alors que la fixture `client` (`tests/conftest.py`) est censée remplacer
`mlflow.xgboost.load_model` par un `DummyModel` factice, sans réseau. Le mock
(`monkeypatch.setattr("mlflow.xgboost.load_model", ...)`) n'était donc pas actif au moment précis
du démarrage de l'application (`lifespan` dans `api/main.py`), uniquement pour ce tout premier
appel de la session de tests.

Élément de contexte : le log CI montre `pytest-9.1.1`, contre `pytest-7.4.3` en local — comme
`requirements.txt` ne fixe aucune version, la CI installe systématiquement les dernières versions
disponibles (dont `mlflow`), ce qui peut faire diverger le comportement d'un environnement à
l'autre. Piste retenue : les versions récentes de MLflow chargent certains modules "flavor"
(`mlflow.xgboost`) en lazy-loading, remplaçant potentiellement le module patché par sa version
réelle au premier accès effectif — écrasant le mock juste avant qu'il ne serve.

**Correction** : plutôt que de tenter de figer une version exacte de `mlflow` (fragile et à
reproduire à chaque mise à jour), la fixture `client` force désormais explicitement le modèle
factice sur l'application une fois le `TestClient` démarré, indépendamment de ce qui s'est passé
pendant le `lifespan` :

```python
with TestClient(app) as c:
    c.app.state.model = DummyModel()
    yield c
```

(`tests/conftest.py`, commit `cfd73c3`, "fix test model mock"). Cette approche est robuste aux
évolutions internes de MLflow, puisqu'elle ne dépend plus de l'endroit exact où le modèle est
chargé en interne.

---

## Incident 3 — écriture des tests d'intégration UI (`tests/test_ui_integration.py`)

**Contexte** : `tests/test_pipeline.py` ne teste que l'API FastAPI en direct (via `TestClient`),
jamais la couche Streamlit qui la consomme (`ui.py`, `views/*.py`, `dashboard_qualite.py`). Un
nouveau fixture `ui_client` (`tests/conftest.py`) redirige `requests.get/post/delete` vers ce même
`TestClient`, pour exécuter les pages Streamlit via `streamlit.testing.v1.AppTest` en intégration
réelle contre l'API (mêmes routes, même DB de test, même modèle factice).

**Deux échecs rencontrés en écrivant ces tests, et leur interprétation** :

1. `test_ui_historique_shows_real_data` échouait avec
   `AttributeError: st.session_state has no attribute "user_id"`, levée depuis
   `views/historique.py:88` (nom du fichier CSV exporté). Interprétation : ce n'est pas un bug de
   l'application — en usage réel, `ui.py` initialise toujours `user_id` à la connexion — mais un
   oubli dans le setup du test (`at.session_state` incomplet). Corrigé en initialisant `user_id`
   avant `at.run()`.
2. `test_ui_securite_admin_rotate_key` échouait avec
   `ValueError: 'ID 2 - client_test (Client)' is not in list` sur `at.selectbox[0].select(...)`.
   Interprétation : `securite_admin.py` contient **deux** `st.selectbox` (le rôle du formulaire de
   création, puis le compte cible de la rotation) — `selectbox[0]` visait le mauvais widget.
   Corrigé en utilisant `selectbox[1]`.

**Couverture obtenue** (12 tests, tous les points de terminaison exploités par l'UI sauf une
exception documentée ci-dessous) :
`POST /api/measurements`, `GET /api/measurements`, `GET /api/clients`, `POST /api/clients`,
`POST /api/clients/{id}/rotate-key`, `GET /api/audit-logs`, `GET /api/dashboard/measurements`,
`GET /api/dashboard/metrics`, `GET /api/dashboard/model-versions`, `GET`/`DELETE /api/me`
(exécutés en une seule passe de script Streamlit, tous les onglets s'exécutant côté serveur
indépendamment de l'onglet visible).

**Correctif appliqué suite à l'incident 3** : `GET`/`DELETE /api/me` (RGPD) existaient côté API
et étaient testées (`test_rgpd_me_get`, `test_rgpd_me_delete`) mais n'étaient exposées dans
**aucune** page Streamlit — un client ne pouvait pas exercer son droit d'accès/suppression RGPD
depuis l'UI. Ajout de `views/mes_donnees.py` (page "Mes Données (RGPD)", US-05) pour combler ce
trou d'intégration, avec confirmation explicite (case à cocher) avant suppression — conforme aux
critères d'accessibilité WCAG 3.3.4 déjà spécifiés dans `notebooks/user_stories.md`.

**Limite assumée, non couverte par ces tests** :
- `POST /api/ocr/lab-report` (bouton OCR de `views/panel_test.py`) : `AppTest` ne simule pas
  l'interaction avec `st.file_uploader`, ce flux reste couvert uniquement côté API
  (`tests/test_pipeline.py::test_ocr_lab_report_success`), pas côté UI.

---

## Incident 4 — `IndexError` sur `POST /api/measurements` (introduit volontairement, épreuve E5/C21)

**Contexte** : contrairement aux incidents 1 à 3, ce bug n'a pas été rencontré par accident — il a
été introduit délibérément sur la branche `bug-e5` pour la démonstration de la compétence C21
(résolution d'un incident technique), conformément à la consigne de l'épreuve ("partez d'une
application existante et introduisez-y une erreur, que vous corrigerez ensuite").

**Bug introduit** (commit `d122f7a`) : dans `api/main.py`, `add_measurement` stockait
`turbidity=f[9]` au lieu de `f[8]`. `FeaturesPayload` valide exactement 9 éléments (`features:
list[float]`, `min_length=9, max_length=9`), donc les indices valides vont de 0 à 8 — `f[9]` est
systématiquement hors limites.

**Reproduit** : exécution locale de `pytest`, échec immédiat et systématique de 2 tests :

```
tests/test_pipeline.py::test_measurements_predict_potable PASSED -> FAILED
tests/test_pipeline.py::test_measurements_predict_non_potable PASSED -> FAILED

E       IndexError: list index out of range
api\main.py:283: IndexError
```

Poussé sur `bug-e5`, confirmé rouge en CI également (run `29654803806`, commit `d122f7a`) — pas
seulement une reproduction locale.

**Diagnostic** : erreur d'indexation d'une ligne (décalage d'un cran sur le dernier champ). Aucun
des indices ne peut dépasser 8 pour une liste de 9 éléments — `f[9]` lève systématiquement
`IndexError`, pour toute requête valide, pas seulement dans certains cas limites.

**Correction** (branche `fix-measurements-indexerror`, commit `52e463d`) : `f[9]` → `f[8]`.

**Test renforcé** : `test_get_measurements_history` ne vérifiait auparavant que le champ `ph` de
l'historique retourné. Il vérifie désormais que les 9 mesures sont persistées à la bonne
position, une par une — ce test aurait détecté cette classe de bug (mauvais index sur
n'importe lequel des 9 champs), pas seulement l'occurrence précise sur `turbidity`. Suite
complète revérifiée : 47/47 en local, CI verte sur `fix-measurements-indexerror` (run
`29654856038`, `conclusion=success`), confirmée via l'API GitHub — le run du commit du bug
(`29654803806`, sur `d122f7a`) est bien rouge (`conclusion=failure`) au même endroit. Branche de
fix ensuite mergée dans `bug-e5`.

**Rejeu contre la stack réelle (C20)** : ce même bug a ensuite été réintroduit temporairement
dans le conteneur `docker-compose` en fonctionnement, avec du trafic soutenu généré sur la route
cassée, pour vérifier que le monitorage système (cf. `docs/monitoring_systeme.md`) détecte
réellement ce genre d'incident. Ce rejeu a révélé un second bug, distinct : `metrics_middleware`
ne comptait pas les crashs non gérés dans les métriques Prometheus (corrigé dans le même commit
que la remise en place du fix, voir `docs/monitoring_systeme.md` pour le détail). Une fois ce
second correctif en place, l'alerte "Taux d'erreurs serveur élevé" est passée par les 3 états
attendus (`Normal` → `Pending` → `Firing`) puis est revenue à `Normal` après redéploiement du
fix — preuve que C20 et C21 se referment l'un sur l'autre en conditions réelles, pas seulement en
théorie.

---

## Résultat final

Run CI complet et vert sur `fix-ci-pytest` (id `28558610639`) : `Validate raw data` → `Run tests`
(32/32) → `Train & validate model (F1-score gate)`, les trois étapes réussissent sans erreur.
Suite complète actuelle (API + intégration UI) : 46/46 tests passés en local et en CI
(run `28603481452` sur `ui-integration-tests`, vert de bout en bout y compris les builds Docker).
