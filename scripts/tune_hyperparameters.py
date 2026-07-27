"""
tune_hyperparameters.py - Recherche aléatoire d'hyperparametres XGBoost (MLflow).

Entraine plusieurs combinaisons d'hyperparametres (SMOTE + XGBoost), toutes evaluees
au meme seuil de decision fixe (DECISION_THRESHOLD), et logge chaque essai comme un
run MLflow separe dans l'experience "water_quality_tuning" pour comparaison visuelle
dans l'UI MLflow. Le critere de classement est le F0.5-score (poids 4x plus fort sur la
precision que sur le recall, cf. RapportE_3/C12) a ce seuil, pas le F1.

N'effectue AUCUNE promotion en Production automatiquement : ce script sert a explorer,
pas a deployer. Une fois le meilleur essai identifie, relancer experiment.py avec ces
hyperparametres si on veut effectivement le promouvoir.
"""

import pickle
import random

import mlflow
import mlflow.xgboost
from imblearn.over_sampling import SMOTE
from mlflow.tracking import MlflowClient
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, precision_score, recall_score
from xgboost import XGBClassifier

mlflow.set_tracking_uri("http://127.0.0.1:5000")
EXPERIMENT_NAME = "water_quality_tuning"
N_TRIALS = 30
DECISION_THRESHOLD = 0.58
RANDOM_SEED = 42

SEARCH_SPACE = {
    "n_estimators": [150, 200, 250, 300, 350, 400, 500],
    "max_depth": [3, 4, 5, 6, 7, 8],
    "learning_rate": [0.01, 0.03, 0.05, 0.08, 0.1, 0.15],
    "subsample": [0.6, 0.7, 0.8, 0.9, 1.0],
    "colsample_bytree": [0.6, 0.7, 0.8, 0.9, 1.0],
    "min_child_weight": [1, 2, 3, 5, 7],
    "gamma": [0.0, 0.1, 0.2, 0.3, 0.5],
    "reg_alpha": [0.0, 0.1, 0.3, 0.5],
    "reg_lambda": [1.0, 1.5, 2.0, 3.0],
}

client = MlflowClient()
experiment = client.get_experiment_by_name(EXPERIMENT_NAME)
experiment_id = experiment.experiment_id if experiment else client.create_experiment(EXPERIMENT_NAME)
mlflow.set_experiment(EXPERIMENT_NAME)

with open("data/processed/processed_data.pkl", "rb") as f:
    data = pickle.load(f)

X_train, X_val = data["X_train"], data["X_val"]
y_train, y_val = data["y_train"], data["y_val"]

smote = SMOTE(random_state=RANDOM_SEED)
X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)

rng = random.Random(RANDOM_SEED)
best_f05, best_params, best_run_id = -1.0, None, None

print(f"Recherche sur {N_TRIALS} combinaisons, seuil fixe = {DECISION_THRESHOLD}\n")

for i in range(N_TRIALS):
    params = {name: rng.choice(values) for name, values in SEARCH_SPACE.items()}
    params.update({"use_label_encoder": False, "eval_metric": "logloss", "random_state": RANDOM_SEED})

    with mlflow.start_run(run_name=f"tuning_trial_{i+1:02d}") as run:
        model = XGBClassifier(**params)
        model.fit(X_train_resampled, y_train_resampled, eval_set=[(X_val, y_val)], verbose=False)

        y_proba = model.predict_proba(X_val)[:, 1]
        y_pred = (y_proba >= DECISION_THRESHOLD).astype(int)

        metrics = {
            "accuracy": accuracy_score(y_val, y_pred),
            "f1_score": f1_score(y_val, y_pred, zero_division=0),
            "f0.5_score": fbeta_score(y_val, y_pred, beta=0.5, zero_division=0),
            "precision": precision_score(y_val, y_pred, zero_division=0),
            "recall": recall_score(y_val, y_pred, zero_division=0),
            "decision_threshold": DECISION_THRESHOLD,
        }

        mlflow.log_params(params)
        mlflow.log_params({"smote": True, "tuning_trial": i + 1})
        mlflow.log_metrics(metrics)

        print(
            f"[{i+1:02d}/{N_TRIALS}] f0.5={metrics['f0.5_score']:.4f}  "
            f"precision={metrics['precision']:.4f}  recall={metrics['recall']:.4f}  "
            f"(n_estimators={params['n_estimators']}, max_depth={params['max_depth']}, "
            f"learning_rate={params['learning_rate']})"
        )

        if metrics["f0.5_score"] > best_f05:
            best_f05 = metrics["f0.5_score"]
            best_params = params
            best_run_id = run.info.run_id

print("\n" + "=" * 60)
print(f"Meilleur essai : run {best_run_id}")
print(f"F0.5-score = {best_f05:.4f}")
print("Hyperparametres :")
for name in SEARCH_SPACE:
    print(f"  {name:20s} : {best_params[name]}")
print("=" * 60)
print(
    f"\nPour deployer ces hyperparametres : reporter ces valeurs dans "
    f"scripts/experiment.py (params_xgb) puis relancer experiment.py."
)
