"""
CageMind — Hyperparameter Tuning con Optuna

Optimiza los 4 modelos usando Optuna (búsqueda inteligente):
  1. Quién gana (binario)
  2. Cómo gana (multiclase: KO/Sub/Dec)
  3. Finish vs Decisión (binario)
  4. En qué round (multiclase, solo finishes)

Para cada modelo prueba Logistic Regression, Random Forest y XGBoost
con diferentes combinaciones de hyperparameters.

Uso:
    python run_hyperparameter_tuning.py
"""
from __future__ import annotations

import json
import pickle
import warnings
import time
from pathlib import Path

import pandas as pd
import numpy as np
import optuna

from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report
)
from xgboost import XGBClassifier

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

DATA_PATH = Path("data/processed/training_dataset_v2.csv")
OUTPUT_DIR = Path("ml/models")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

N_TRIALS = 80  # Trials por modelo
CV_FOLDS = 5
RANDOM_STATE = 42


# ============================================================
# CARGA DE DATOS
# ============================================================
def load_data():
    print("Cargando dataset v2...")
    df = pd.read_csv(DATA_PATH)
    print(f"  Shape: {df.shape}")

    meta_cols = ["fight_id", "date", "fighter_a", "fighter_b", "weight_class",
                 "target_winner", "target_method", "target_round", "target_goes_distance",
                 "a_last_weight_class", "b_last_weight_class"]

    drop_cols = [c for c in df.columns if "cardio_ratio" in c]
    feature_cols = [c for c in df.columns if c not in meta_cols and c not in drop_cols]

    X = df[feature_cols].select_dtypes(include=[np.number]).copy()
    feature_names = list(X.columns)
    print(f"  Features: {len(feature_names)}")

    y_winner = df["target_winner"].values
    y_method = df["target_method"].values
    y_distance = df["target_goes_distance"].values
    y_round = df["target_round"].values

    return df, X.values, feature_names, y_winner, y_method, y_distance, y_round


# ============================================================
# OBJECTIVE FUNCTIONS (Optuna)
# ============================================================
def create_objective(X, y, is_multiclass=False):
    """Crea la función objetivo para Optuna."""
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = "f1_weighted" if is_multiclass else "accuracy"

    def objective(trial):
        algo = trial.suggest_categorical("algorithm", ["logistic", "rf", "xgb"])

        if algo == "logistic":
            C = trial.suggest_float("lr_C", 0.001, 100.0, log=True)
            penalty = trial.suggest_categorical("lr_penalty", ["l1", "l2"])
            solver = "saga" if penalty == "l1" else trial.suggest_categorical("lr_solver", ["lbfgs", "saga"])
            model = LogisticRegression(
                C=C, penalty=penalty, solver=solver,
                max_iter=2000, random_state=RANDOM_STATE,
                multi_class="multinomial" if is_multiclass else "auto"
            )

        elif algo == "rf":
            model = RandomForestClassifier(
                n_estimators=trial.suggest_int("rf_n_estimators", 100, 800, step=50),
                max_depth=trial.suggest_int("rf_max_depth", 4, 25),
                min_samples_split=trial.suggest_int("rf_min_samples_split", 2, 30),
                min_samples_leaf=trial.suggest_int("rf_min_samples_leaf", 1, 20),
                max_features=trial.suggest_categorical("rf_max_features", ["sqrt", "log2", 0.3, 0.5, 0.7]),
                random_state=RANDOM_STATE,
                n_jobs=-1
            )

        else:  # xgb
            model = XGBClassifier(
                n_estimators=trial.suggest_int("xgb_n_estimators", 100, 800, step=50),
                max_depth=trial.suggest_int("xgb_max_depth", 3, 12),
                learning_rate=trial.suggest_float("xgb_learning_rate", 0.01, 0.3, log=True),
                subsample=trial.suggest_float("xgb_subsample", 0.5, 1.0),
                colsample_bytree=trial.suggest_float("xgb_colsample_bytree", 0.3, 1.0),
                reg_alpha=trial.suggest_float("xgb_reg_alpha", 1e-8, 10.0, log=True),
                reg_lambda=trial.suggest_float("xgb_reg_lambda", 1e-8, 10.0, log=True),
                min_child_weight=trial.suggest_int("xgb_min_child_weight", 1, 10),
                gamma=trial.suggest_float("xgb_gamma", 0.0, 5.0),
                random_state=RANDOM_STATE,
                use_label_encoder=False,
                eval_metric="mlogloss" if is_multiclass else "logloss",
                verbosity=0,
                n_jobs=-1
            )

        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", model),
        ])

        scores = cross_val_score(pipeline, X, y, cv=skf, scoring=scoring)
        return scores.mean()

    return objective


# ============================================================
# ENTRENAR MODELO OPTIMIZADO
# ============================================================
def train_optimized(name, X, y, is_multiclass=False, n_trials=N_TRIALS):
    """Ejecuta Optuna y retorna el mejor pipeline entrenado."""
    print(f"\n{'='*60}")
    print(f"OPTIMIZANDO: {name}")
    print(f"{'='*60}")
    print(f"  Samples: {len(y)} | Trials: {n_trials}")

    start = time.time()

    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE))
    objective = create_objective(X, y, is_multiclass)
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    elapsed = time.time() - start
    best = study.best_trial

    print(f"\n  Tiempo: {elapsed:.1f}s")
    print(f"  Mejor score (CV): {best.value:.4f}")
    print(f"  Algoritmo: {best.params['algorithm']}")
    print(f"  Params: {json.dumps({k:v for k,v in best.params.items() if k != 'algorithm'}, indent=4, default=str)}")

    # Reconstruir el mejor modelo
    params = best.params
    algo = params["algorithm"]

    if algo == "logistic":
        penalty = params["lr_penalty"]
        solver = params.get("lr_solver", "saga")
        if penalty == "l1":
            solver = "saga"
        model = LogisticRegression(
            C=params["lr_C"], penalty=penalty, solver=solver,
            max_iter=2000, random_state=RANDOM_STATE,
            multi_class="multinomial" if is_multiclass else "auto"
        )
    elif algo == "rf":
        model = RandomForestClassifier(
            n_estimators=params["rf_n_estimators"],
            max_depth=params["rf_max_depth"],
            min_samples_split=params["rf_min_samples_split"],
            min_samples_leaf=params["rf_min_samples_leaf"],
            max_features=params["rf_max_features"],
            random_state=RANDOM_STATE, n_jobs=-1
        )
    else:
        model = XGBClassifier(
            n_estimators=params["xgb_n_estimators"],
            max_depth=params["xgb_max_depth"],
            learning_rate=params["xgb_learning_rate"],
            subsample=params["xgb_subsample"],
            colsample_bytree=params["xgb_colsample_bytree"],
            reg_alpha=params["xgb_reg_alpha"],
            reg_lambda=params["xgb_reg_lambda"],
            min_child_weight=params["xgb_min_child_weight"],
            gamma=params["xgb_gamma"],
            random_state=RANDOM_STATE,
            use_label_encoder=False,
            eval_metric="mlogloss" if is_multiclass else "logloss",
            verbosity=0, n_jobs=-1
        )

    pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])

    # Evaluación en test set
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    test_acc = accuracy_score(y_test, y_pred)
    avg = "weighted" if is_multiclass else "binary"
    test_f1 = f1_score(y_test, y_pred, average=avg, zero_division=0)

    print(f"\n  Test Accuracy: {test_acc:.4f}")
    print(f"  Test F1: {test_f1:.4f}")

    if not is_multiclass and hasattr(pipeline, "predict_proba"):
        y_proba = pipeline.predict_proba(X_test)[:, 1]
        roc = roc_auc_score(y_test, y_proba)
        print(f"  Test ROC-AUC: {roc:.4f}")

    # Entrenar final en TODO el dataset
    final_pipeline = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])
    final_pipeline.fit(X, y)

    result = {
        "name": name,
        "algorithm": algo,
        "best_cv_score": round(best.value, 4),
        "test_accuracy": round(test_acc, 4),
        "test_f1": round(test_f1, 4),
        "best_params": params,
        "n_trials": n_trials,
        "time_seconds": round(elapsed, 1),
    }

    return final_pipeline, result, study


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("CAGEMIND — HYPERPARAMETER TUNING CON OPTUNA")
    print("=" * 60)

    df, X, feature_names, y_winner, y_method, y_distance, y_round = load_data()

    all_results = {}

    # ── MODELO 1: Quién gana ──
    winner_pipeline, winner_result, _ = train_optimized(
        "Modelo 1: Quién gana", X, y_winner, is_multiclass=False
    )
    all_results["winner"] = winner_result

    # ── MODELO 2: Cómo gana ──
    mask_method = np.array([m in ["ko", "sub", "dec"] for m in y_method])
    X_method = X[mask_method]
    y_m = y_method[mask_method]
    le = LabelEncoder()
    y_method_encoded = le.fit_transform(y_m)
    print(f"\n  Method classes: {list(le.classes_)}")

    method_pipeline, method_result, _ = train_optimized(
        "Modelo 2: Cómo gana", X_method, y_method_encoded, is_multiclass=True
    )
    all_results["method"] = method_result

    # ── MODELO 3: Finish vs Decisión ──
    distance_pipeline, distance_result, _ = train_optimized(
        "Modelo 3: Finish vs Decisión", X, y_distance, is_multiclass=False
    )
    all_results["distance"] = distance_result

    # ── MODELO 4: En qué round ──
    mask_finish = np.array([m in ["ko", "sub"] for m in y_method])
    X_round = X[mask_finish]
    y_r = y_round[mask_finish]
    valid = ~pd.isna(y_r)
    X_round = X_round[valid]
    y_r = y_r[valid].astype(int)
    y_r[y_r >= 4] = 4
    y_r = y_r - 1

    round_pipeline, round_result, _ = train_optimized(
        "Modelo 4: En qué round", X_round, y_r, is_multiclass=True
    )
    all_results["round"] = round_result

    # ── GUARDAR MODELOS ──
    print(f"\n{'='*60}")
    print("GUARDANDO MODELOS OPTIMIZADOS")
    print(f"{'='*60}")

    models_bundle = {
        "winner_model": winner_pipeline,
        "method_model": method_pipeline,
        "method_encoder": le,
        "distance_model": distance_pipeline,
        "round_model": round_pipeline,
        "feature_names": feature_names,
    }

    bundle_path = OUTPUT_DIR / "ufc_predictor_models_tuned.pkl"
    with open(bundle_path, "wb") as f:
        pickle.dump(models_bundle, f)
    print(f"  Modelos guardados: {bundle_path}")

    with open(OUTPUT_DIR / "feature_names.json", "w") as f:
        json.dump(feature_names, f, indent=2)

    with open(OUTPUT_DIR / "tuning_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Resultados: {OUTPUT_DIR / 'tuning_results.json'}")

    # ── RESUMEN ──
    print(f"\n{'='*60}")
    print("RESUMEN — ANTES vs DESPUÉS")
    print(f"{'='*60}")

    # Accuracies originales del doc
    original = {
        "winner": 64.79,
        "method": 53.18,
        "distance": 57.95,
        "round": 47.43,
    }

    for key, label in [("winner", "Quién gana"), ("method", "Cómo gana"),
                        ("distance", "Finish vs Dec"), ("round", "En qué round")]:
        old = original[key]
        new = all_results[key]["best_cv_score"] * 100
        diff = new - old
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="
        print(f"  {label:20s}  Antes: {old:.2f}%  →  Después: {new:.2f}%  ({arrow} {abs(diff):.2f}pp)")

    print(f"\n{'='*60}")
    print("TUNING COMPLETADO")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()