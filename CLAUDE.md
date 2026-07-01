# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Waterflow 2 is an MLOps platform that predicts water **potability** (potable/non potable) from 9
physico-chemical measurements (ph, hardness, solids, chloramines, sulfate, conductivity,
organic_carbon, trihalomethanes, turbidity), using an XGBoost model tracked and served through
MLflow's Model Registry. It exposes a FastAPI backend, a Streamlit UI, and OCR-based ingestion of
lab report images/PDFs.

## Running the stack

Three services must run together (in this order, each in its own terminal / background process):

```bash
# 1. MLflow tracking server + model registry (UI at http://127.0.0.1:5000)
python -m mlflow server --host 127.0.0.1 --port 5000

# 2. FastAPI backend (loads the "Production" stage of water_quality_model from MLflow at startup)
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# 3. Streamlit UI (http://localhost:8501), talks to the API at 127.0.0.1:8000
python -m streamlit run ui.py
```

`waterflow2.bat` starts mlflow ui + `app.py` + streamlit together, but `app.py` (a Flask entry
point referenced by the README and by `tests/test_pipeline.py`) does not currently exist in the
repo root — the FastAPI app in `api/main.py` is the actual live backend. Treat `app.py` /
`tests/test_pipeline.py` as stale/legacy until reconciled with the FastAPI implementation.

First-time setup: create the first Admin API key with `python init_admin.py` (prints the plain-text
key once — it's only ever stored as a SHA-256 hash in the DB).

Training a new model version: `python experiment.py` (loads `data/processed/processed_data.pkl`,
applies SMOTE, trains XGBoost, logs params/metrics/model to MLflow, registers it as
`water_quality_model`, and transitions the newest version to the `Production` stage — this
immediately affects what the running API serves next time it (re)loads the model).

## Tests

```bash
pytest tests/
```

Note: `tests/test_pipeline.py` imports `from app import app, BEST_THRESHOLD` — a Flask app that no
longer exists in this repo (the project migrated to FastAPI in `api/main.py`). This test file will
fail to collect until it's rewritten against the FastAPI app (e.g. with `TestClient`).

## Architecture

- **`api/main.py`** — FastAPI app. Loads the MLflow `Production` model once at startup
  (`lifespan`), and applies a fixed decision threshold (`app.state.best_threshold`, currently
  0.37) to `predict_proba` output rather than the model's default 0.5 cutoff. A single HTTP
  middleware (`access_log`) writes every request to the `audit_logs` table, resolving the
  requesting user by re-hashing the `X-API-Key` header and matching it against stored hashes.
- **`api/auth.py`** — shared `get_current_user` / `require_role(*roles)` FastAPI dependencies used
  by both `api/main.py` and `api/ocr_router.py`. Auth is API-key based (`X-API-Key` header,
  SHA-256 hashed, looked up in the `users` table); roles are `Client`, `Quality_Analyst`, `Admin`.
  Only the Admin role can create/list clients, rotate keys, or read audit logs; Quality_Analyst and
  Admin can hit the `/api/dashboard/*` routes.
- **`api/ocr_router.py`** — `/api/ocr/lab-report` sends an uploaded image/PDF to the OCR.space API,
  regex-parses the returned text for the same 9 features (plus a few extra fields like nitrates),
  and runs the same prediction path as `/api/measurements`. The client_id always comes from the
  authenticated API key, never from OCR/user input (deliberate RGPD-safety choice).
- **`data/db/WaterFlowDB.py`** — the only data-access layer, wrapping a single SQLite file at
  `data/db/waterflow.db`. Tables: `users` (api_key stored as SHA-256 hash, `right` = role,
  `is_active` supports key revocation), `prediction` (one row per measurement + potability result +
  `source`: `manuel` or `ocr`), `performance_metrics`, `audit_logs`. `_ensure_prediction_columns()`
  runs a soft migration (adds columns if missing) on every connect — there is no separate migration
  tool. Every route opens/closes its own `WaterFlowDB()` connection rather than sharing one.
- **`experiment.py`** — standalone MLflow training script (not imported by the API): loads
  preprocessed train/val split, balances classes with SMOTE, trains XGBoost, sweeps thresholds
  0.30–0.70 for best F1, logs everything to the `experiment_water_quality` MLflow experiment, and
  registers + promotes the model to `Production`. The threshold found here must be manually kept in
  sync with `app.state.best_threshold` in `api/main.py`.
- **`ui.py` + `views/`** — Streamlit multi-page app. Role read out of the API's `/api/login`
  response drives which pages (`st.navigation`) are shown: `Admin` gets
  `views/accueil_admin.py` + `views/securite_admin.py`; `Quality_Analyst` gets
  `dashboard_qualite.py`; everyone else (`Client`) gets `views/panel_test.py` +
  `views/historique.py`. Session state (`st.session_state`) holds the API key and is sent as
  `X-API-Key` on every backend call — there's no server-side session.
- **`data/`** — `raw/` has the source Kaggle-style CSV; `processed/` has the pickled
  train/val/test split consumed by `experiment.py`; `description/` and `output/` hold notes and
  EDA plots from the notebooks in `notebooks/`.
- **`src/main.py`, `src/model.py`** — currently empty placeholder files.

## Conventions to preserve

- API responses and in-code comments are in French; keep new endpoints/docstrings consistent with
  that style (see the `tags=[...]` groupings in `api/main.py`: Auth, Prélèvements, Clients, RGPD,
  Dashboard, Admin).
- API keys are only ever returned in plaintext once (on creation or key rotation) — never re-log or
  persist the plaintext value anywhere else.
- RGPD endpoints (`/api/me` GET/DELETE) matter to this project: account deletion anonymizes
  `audit_logs.user_id` to NULL instead of deleting audit rows, while actually deleting the user's
  `prediction`/`performance_metrics` rows.
