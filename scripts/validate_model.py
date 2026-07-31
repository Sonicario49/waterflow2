"""
validate_model.py - Entraînement + validation du modèle (étape CI, gate qualité).

Rejoue la même logique que experiment.py (SMOTE + XGBoost + seuil de décision fixe)
mais sans dépendance à un serveur MLflow : rien n'est loggé ni promu en Production ici,
c'est juste un contrôle de non-régression avant merge.

Le gate verifie le F0.5-score, pas le F1 : la priorite du projet est de minimiser les
faux positifs "potable" (eau non potable classee a tort comme sure), donc la precision
pese 4x plus que le recall dans la moyenne harmonique ponderee du F0.5 (poids 0.8 vs
0.2, cf. RapportE_3, C12).
"""

import pickle
import sys

from imblearn.over_sampling import SMOTE
from sklearn.metrics import accuracy_score, f1_score, fbeta_score, precision_score, recall_score
from xgboost import XGBClassifier

PROCESSED_DATA_PATH = "data/processed/processed_data.pkl"
MIN_F05_SCORE = 0.50

PARAMS_XGB = {
    # Issus de scripts/tune_hyperparameters.py (recherche aleatoire, 30 essais,
    # critere F0.5 au seuil 0.58) -- cf. experiment.py pour le detail.
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.03,
    "subsample": 1.0,
    "colsample_bytree": 1.0,
    "min_child_weight": 1,
    "gamma": 0.5,
    "reg_alpha": 0.3,
    "reg_lambda": 3.0,
    "eval_metric": "logloss",
    "random_state": 42,
}


def main() -> int:
    with open(PROCESSED_DATA_PATH, "rb") as f:
        data = pickle.load(f)

    X_train, X_val = data["X_train"], data["X_val"]
    y_train, y_val = data["y_train"], data["y_val"]

    X_train_resampled, y_train_resampled = SMOTE(random_state=42).fit_resample(X_train, y_train)

    model = XGBClassifier(**PARAMS_XGB)
    model.fit(X_train_resampled, y_train_resampled, eval_set=[(X_val, y_val)], verbose=False)

    y_proba = model.predict_proba(X_val)[:, 1]

    # Seuil de decision fixe a 0.58 (meme choix deliberement securitaire que
    # experiment.py, cf. commentaire la-bas) : maximise le F0.5 (precision 4x
    # plus pesante que le recall dans la moyenne harmonique ponderee) plutot
    # qu'un balayage qui maximiserait le F1, moins adapte a un cas d'usage
    # securitaire.
    best_threshold = 0.58
    y_pred = (y_proba >= best_threshold).astype(int)
    f05 = fbeta_score(y_val, y_pred, beta=0.5, zero_division=0)
    metrics = {
        "accuracy": accuracy_score(y_val, y_pred),
        "f1_score": f1_score(y_val, y_pred, zero_division=0),
        "f0.5_score": f05,
        "precision": precision_score(y_val, y_pred, zero_division=0),
        "recall": recall_score(y_val, y_pred, zero_division=0),
        "best_threshold": best_threshold,
    }

    print("Validation du modèle (SMOTE + XGBoost) :")
    for name, val in metrics.items():
        print(f"  {name:15s} : {val:.4f}")

    if f05 < MIN_F05_SCORE:
        print(f"\nÉchec : F0.5-score {f05:.4f} < seuil minimal {MIN_F05_SCORE}.")
        return 1

    print(f"\nOK : F0.5-score {f05:.4f} >= seuil minimal {MIN_F05_SCORE}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())