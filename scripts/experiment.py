import pickle
import mlflow
import mlflow.xgboost
from xgboost import XGBClassifier
from mlflow.tracking import MlflowClient
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, precision_score, recall_score
from imblearn.over_sampling import SMOTE

# ──────────────────────────────────────────────
# Setup MLflow
# ──────────────────────────────────────────────
mlflow.set_tracking_uri("http://127.0.0.1:5000")
EXPERIMENT_NAME = "experiment_water_quality"
client = MlflowClient()

experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
if experiment is None:
    experiment_id = client.create_experiment(EXPERIMENT_NAME)
else:
    experiment_id = experiment.experiment_id

mlflow.set_experiment(EXPERIMENT_NAME)

# ──────────────────────────────────────────────
# Chargement des données
# ──────────────────────────────────────────────
with open("data/processed/processed_data.pkl", "rb") as f:
    data = pickle.load(f)

X_train = data["X_train"]
X_val   = data["X_val"]
y_train = data["y_train"]
y_val   = data["y_val"]

print(f"Distribution train — 0: {(y_train==0).sum()} | 1: {(y_train==1).sum()}")

# ──────────────────────────────────────────────
# 
# ──────────────────────────────────────────────
smote = SMOTE(random_state=42)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

print(f"Après SMOTE      — 0: {(y_train_resampled==0).sum()} | 1: {(y_train_resampled==1).sum()}")

# ──────────────────────────────────────────────
# Paramètres XGBoost optimisés
# ──────────────────────────────────────────────
params_xgb = {
    # Issus de scripts/tune_hyperparameters.py (recherche aleatoire, 30 essais,
    # critere F0.5 au seuil 0.58) -- meilleur essai trouve, cf. run MLflow
    # e2f517cbf3b24134a117c543fd067907 (experience "water_quality_tuning").
    "n_estimators":     200,
    "max_depth":        5,
    "learning_rate":    0.03,
    "subsample":        1.0,
    "colsample_bytree": 1.0,
    "min_child_weight": 1,
    "gamma":            0.5,
    "reg_alpha":        0.3,
    "reg_lambda":       3.0,
    "use_label_encoder": False,
    "eval_metric":      "logloss",
    "random_state":     42,
}

# ──────────────────────────────────────────────
# Run MLflow
# ──────────────────────────────────────────────
with mlflow.start_run(run_name="XGBoost_SMOTE_Optimise") as run:

    model = XGBClassifier(**params_xgb)
    model.fit(
        X_train_resampled, y_train_resampled,
        eval_set=[(X_val, y_val)],
        verbose=False,
    )

 
    y_proba = model.predict_proba(X_val)[:, 1]

    # Seuil de decision fixe a 0.58, choisi deliberement plutot que par un
    # balayage qui maximiserait le F1 : un balayage 0.30-0.70 maximisant le F1
    # atterrit sur 0.37, qui produit plus de faux positifs "potable" (eau non
    # potable classee a tort comme sure) que de faux negatifs a ce seuil -- pas
    # le bon compromis pour un cas d'usage securitaire. 0.58 maximise le F0.5
    # (poids 0.8 sur la precision contre 0.2 sur le recall dans la moyenne
    # harmonique ponderee -- soit 4x plus de poids sur la precision) -- cf.
    # scripts/tune_hyperparameters.py pour la recherche qui a mene a ce choix.
    best_threshold = 0.58

    print(f"\n   Seuil de decision retenu : {best_threshold:.2f}")

    y_pred = (y_proba >= best_threshold).astype(int)

    metrics = {
        "accuracy":       accuracy_score(y_val, y_pred),
        "f1_score":       f1_score(y_val, y_pred, zero_division=0),
        "f0.5_score":     fbeta_score(y_val, y_pred, beta=0.5, zero_division=0),
        "precision":      precision_score(y_val, y_pred, zero_division=0),
        "recall":         recall_score(y_val, y_pred, zero_division=0),
        "best_threshold": best_threshold,
    }

    mlflow.log_params(params_xgb)
    mlflow.log_params({"smote": True, "threshold_tuning": True})
    mlflow.log_metrics(metrics)

    mlflow.xgboost.log_model(
        xgb_model=model,
        artifact_path="model",
        registered_model_name="water_quality_model",
    )

    print(f"\nRun ID : {run.info.run_id}")
    for name, val in metrics.items():
        print(f"   {name:15s} : {val:.4f}")

# ──────────────────────────────────────────────
#          Transition vers Production
# ──────────────────────────────────────────────
# get_latest_versions() sans filtre de stage renvoie une version "latest" par
# stage existant (Production/None/Archived...), pas forcement celle de CE run --
# on cherche explicitement la version enregistree par le run qu'on vient de
# faire, via son run_id, pour ne jamais promouvoir la mauvaise version.
new_version = client.search_model_versions(f"run_id='{run.info.run_id}'")[0]
latest_version = new_version.version

client.transition_model_version_stage(
    name="water_quality_model",
    version=latest_version,
    stage="Production",
)
print(f"\n Modèle v{latest_version} → Production")