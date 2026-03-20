"""
CageMind — Semana 1: Feature Selection + Re-entrenamiento Completo

Ejecuta las 2 tareas restantes de Semana 1 en un solo script:

1. FEATURE SELECTION
   - Elimina features 100% nulas (cardio_ratio)
   - Elimina features redundantes (correlación > 0.95 entre sí)
   - Rankea por importancia usando XGBoost feature importance
   - Reduce de 167 a ~80-100 features

2. RE-ENTRENAMIENTO (4 modelos)
   - Modelo 1 (Winner): Mejor entre LogReg y XGBoost + Platt Scaling
   - Modelo 2 (Método): XGBoost multiclase con Optuna (reemplaza LogReg)
   - Modelo 3 (Finish vs Dec): Mejor entre RF y XGBoost con Optuna
   - Modelo 4 (Round): XGBoost con Optuna

Requisitos:
    pip install scikit-learn xgboost optuna pandas numpy matplotlib

Uso:
    cd cagemind
    python run_semana1_final.py

Tiempo estimado: ~20-40 minutos (depende de N_TRIALS)
"""
from __future__ import annotations

import json
import pickle
import warnings
import time
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
import optuna

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.model_selection import (
    cross_val_score, StratifiedKFold, train_test_split
)
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score, f1_score, brier_score_loss, roc_auc_score
)
from xgboost import XGBClassifier

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ============================================================
# CONFIGURACIÓN
# ============================================================

PROJECT_ROOT = Path(__file__).parent
DATASET_PATH = PROJECT_ROOT / "data" / "processed" / "training_dataset_v2.csv"
DATASET_V1 = PROJECT_ROOT / "data" / "processed" / "training_dataset.csv"
MODELS_PATH = PROJECT_ROOT / "ml" / "models" / "ufc_predictor_models.pkl"
FEATURES_PATH = PROJECT_ROOT / "ml" / "models" / "feature_names.json"
OUTPUT_DIR = PROJECT_ROOT / "ml" / "semana1"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Tuning config
N_TRIALS = 60          # Trials por modelo (60 ≈ 15-25 min por modelo)
CV_FOLDS = 5
RANDOM_STATE = 42
PROB_CAP = 0.85

# Feature selection config
CORR_THRESHOLD = 0.95  # Eliminar features con correlación > 0.95
MIN_IMPORTANCE = 0.001 # Mínima importancia para mantener feature
TARGET_FEATURES = 90   # Meta: ~90 features (flexible)


# ============================================================
# 1. CARGA DE DATOS
# ============================================================

def load_data():
    """Carga el dataset."""
    path = DATASET_PATH if DATASET_PATH.exists() else DATASET_V1
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró dataset. Ejecuta run_phase3_features.py primero."
        )
    print(f"Dataset: {path}")
    df = pd.read_csv(path)
    print(f"  Shape: {df.shape[0]} peleas, {df.shape[1]} columnas")
    return df


def get_feature_columns(df):
    """Obtener columnas de features numéricas."""
    exclude = {
        "fighter_a", "fighter_b", "fight_id", "event_id", "date",
        "target_winner", "target_method", "target_round",
        "target_goes_distance", "weight_class",
        "a_last_weight_class", "b_last_weight_class",
    }
    numeric = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric if c not in exclude]


# ============================================================
# 2. FEATURE SELECTION
# ============================================================

def feature_selection(df, feature_cols):
    """
    Reduce features en 3 pasos:
    1. Eliminar 100% nulas
    2. Eliminar redundantes (correlación > threshold)
    3. Rankear por importancia XGBoost y recortar
    """
    print("\n" + "=" * 60)
    print("FEATURE SELECTION")
    print("=" * 60)
    original_count = len(feature_cols)

    X = df[feature_cols].copy()
    y = df["target_winner"].dropna()
    mask = y.index.isin(X.index)
    X = X.loc[y.index]

    # Paso 1: Eliminar 100% nulas
    all_null = X.columns[X.isnull().all()].tolist()
    if all_null:
        print(f"\n  Paso 1: Eliminando {len(all_null)} features 100% nulas:")
        for c in all_null:
            print(f"    - {c}")
        X = X.drop(columns=all_null)
        feature_cols = [c for c in feature_cols if c not in all_null]
    else:
        print(f"\n  Paso 1: 0 features 100% nulas")

    # Paso 2: Eliminar redundantes por correlación
    print(f"\n  Paso 2: Buscando features con correlación > {CORR_THRESHOLD}...")
    imputer = SimpleImputer(strategy="median")
    X_imp = pd.DataFrame(imputer.fit_transform(X), columns=X.columns, index=X.index)

    corr_matrix = X_imp.corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

    to_drop_corr = set()
    pairs_found = []
    for col in upper.columns:
        high_corr = upper[col][upper[col] > CORR_THRESHOLD]
        for other_col, corr_val in high_corr.items():
            # Mantener el que tiene mayor correlación con el target
            corr_a_target = abs(X_imp[col].corr(y.astype(float)))
            corr_b_target = abs(X_imp[other_col].corr(y.astype(float)))
            drop_col = other_col if corr_a_target >= corr_b_target else col
            to_drop_corr.add(drop_col)
            pairs_found.append((col, other_col, corr_val, drop_col))

    if to_drop_corr:
        print(f"    Encontradas {len(pairs_found)} pares con corr > {CORR_THRESHOLD}")
        print(f"    Eliminando {len(to_drop_corr)} features redundantes:")
        for c in sorted(to_drop_corr)[:10]:
            print(f"      - {c}")
        if len(to_drop_corr) > 10:
            print(f"      ... y {len(to_drop_corr) - 10} más")

        X_imp = X_imp.drop(columns=to_drop_corr)
        feature_cols = [c for c in feature_cols if c not in to_drop_corr]
    else:
        print(f"    0 features redundantes encontradas")

    print(f"    Features restantes: {len(feature_cols)}")

    # Paso 3: Rankear por importancia XGBoost
    print(f"\n  Paso 3: Rankeando por importancia XGBoost...")
    xgb_ranker = XGBClassifier(
        n_estimators=200, max_depth=5, learning_rate=0.1,
        random_state=RANDOM_STATE, eval_metric="logloss", verbosity=0
    )
    xgb_ranker.fit(X_imp[feature_cols], y.astype(int))
    importances = pd.Series(xgb_ranker.feature_importances_, index=feature_cols)
    importances = importances.sort_values(ascending=False)

    # Mostrar top 20
    print(f"\n    Top 20 features más importantes:")
    for i, (feat, imp) in enumerate(importances.head(20).items()):
        print(f"      {i+1:2d}. {feat:40s} {imp:.4f}")

    # Decidir cuántas mantener
    # Opción: mantener todas con importancia > MIN_IMPORTANCE, o top TARGET_FEATURES
    above_min = importances[importances > MIN_IMPORTANCE]
    n_keep = min(max(len(above_min), TARGET_FEATURES), len(feature_cols))

    # Si hay más de TARGET_FEATURES con importancia > threshold, mantener todas
    # Si hay menos, usar TARGET_FEATURES como mínimo
    selected = importances.head(n_keep).index.tolist()

    print(f"\n    Features con importancia > {MIN_IMPORTANCE}: {len(above_min)}")
    print(f"    Features seleccionadas: {len(selected)}")

    # Guardar ranking completo
    ranking_path = OUTPUT_DIR / "feature_ranking.csv"
    ranking_df = pd.DataFrame({
        "feature": importances.index,
        "importance": importances.values,
        "selected": [f in selected for f in importances.index]
    })
    ranking_df.to_csv(ranking_path, index=False)
    print(f"    Ranking guardado: {ranking_path}")

    print(f"\n  RESUMEN: {original_count} → {len(selected)} features ({original_count - len(selected)} eliminadas)")

    return selected


# ============================================================
# 3. OPTUNA TUNING HELPERS
# ============================================================

def create_xgb_objective(X, y, is_multiclass=False):
    """Objetivo Optuna solo para XGBoost (el plan pide XGBoost para método)."""
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = "f1_weighted" if is_multiclass else "accuracy"

    def objective(trial):
        model = XGBClassifier(
            n_estimators=trial.suggest_int("n_estimators", 100, 600, step=50),
            max_depth=trial.suggest_int("max_depth", 3, 10),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            subsample=trial.suggest_float("subsample", 0.5, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.3, 1.0),
            reg_alpha=trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            reg_lambda=trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
            min_child_weight=trial.suggest_int("min_child_weight", 1, 10),
            gamma=trial.suggest_float("gamma", 0.0, 5.0),
            random_state=RANDOM_STATE,
            eval_metric="mlogloss" if is_multiclass else "logloss",
            verbosity=0, n_jobs=-1,
        )
        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", model),
        ])
        scores = cross_val_score(pipeline, X, y, cv=skf, scoring=scoring)
        return scores.mean()

    return objective


def create_multi_algo_objective(X, y, is_multiclass=False):
    """Objetivo Optuna que prueba LogReg, RF y XGBoost."""
    skf = StratifiedKFold(n_splits=CV_FOLDS, shuffle=True, random_state=RANDOM_STATE)
    scoring = "f1_weighted" if is_multiclass else "accuracy"

    def objective(trial):
        algo = trial.suggest_categorical("algorithm", ["logistic", "rf", "xgb"])

        if algo == "logistic":
            model = LogisticRegression(
                C=trial.suggest_float("lr_C", 0.001, 100.0, log=True),
                penalty="l2", solver="lbfgs",
                max_iter=2000, random_state=RANDOM_STATE,
            )
        elif algo == "rf":
            model = RandomForestClassifier(
                n_estimators=trial.suggest_int("rf_n_estimators", 100, 600, step=50),
                max_depth=trial.suggest_int("rf_max_depth", 4, 20),
                min_samples_split=trial.suggest_int("rf_min_samples_split", 2, 30),
                min_samples_leaf=trial.suggest_int("rf_min_samples_leaf", 1, 20),
                max_features=trial.suggest_categorical("rf_max_features", ["sqrt", "log2", 0.3, 0.5]),
                random_state=RANDOM_STATE, n_jobs=-1,
            )
        else:
            model = XGBClassifier(
                n_estimators=trial.suggest_int("xgb_n_estimators", 100, 600, step=50),
                max_depth=trial.suggest_int("xgb_max_depth", 3, 10),
                learning_rate=trial.suggest_float("xgb_lr", 0.01, 0.3, log=True),
                subsample=trial.suggest_float("xgb_subsample", 0.5, 1.0),
                colsample_bytree=trial.suggest_float("xgb_colsample", 0.3, 1.0),
                reg_alpha=trial.suggest_float("xgb_alpha", 1e-8, 10.0, log=True),
                reg_lambda=trial.suggest_float("xgb_lambda", 1e-8, 10.0, log=True),
                min_child_weight=trial.suggest_int("xgb_min_child", 1, 10),
                gamma=trial.suggest_float("xgb_gamma", 0.0, 5.0),
                random_state=RANDOM_STATE, eval_metric="logloss", verbosity=0, n_jobs=-1,
            )

        pipeline = Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", model),
        ])
        scores = cross_val_score(pipeline, X, y, cv=skf, scoring=scoring)
        return scores.mean()

    return objective


def build_best_pipeline(study, is_multiclass=False):
    """Reconstruye el mejor pipeline a partir de los resultados de Optuna."""
    params = study.best_trial.params
    algo = params.get("algorithm", "xgb")

    if algo == "logistic":
        model = LogisticRegression(
            C=params["lr_C"], penalty="l2", solver="lbfgs",
            max_iter=2000, random_state=RANDOM_STATE,
        )
    elif algo == "rf":
        model = RandomForestClassifier(
            n_estimators=params["rf_n_estimators"],
            max_depth=params["rf_max_depth"],
            min_samples_split=params["rf_min_samples_split"],
            min_samples_leaf=params["rf_min_samples_leaf"],
            max_features=params["rf_max_features"],
            random_state=RANDOM_STATE, n_jobs=-1,
        )
    else:
        # XGBoost - handle both naming conventions
        model = XGBClassifier(
            n_estimators=params.get("n_estimators", params.get("xgb_n_estimators", 200)),
            max_depth=params.get("max_depth", params.get("xgb_max_depth", 5)),
            learning_rate=params.get("learning_rate", params.get("xgb_lr", 0.1)),
            subsample=params.get("subsample", params.get("xgb_subsample", 0.8)),
            colsample_bytree=params.get("colsample_bytree", params.get("xgb_colsample", 0.8)),
            reg_alpha=params.get("reg_alpha", params.get("xgb_alpha", 1e-6)),
            reg_lambda=params.get("reg_lambda", params.get("xgb_lambda", 1.0)),
            min_child_weight=params.get("min_child_weight", params.get("xgb_min_child", 1)),
            gamma=params.get("gamma", params.get("xgb_gamma", 0.0)),
            random_state=RANDOM_STATE,
            eval_metric="mlogloss" if is_multiclass else "logloss",
            verbosity=0, n_jobs=-1,
        )

    return Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", model),
    ])


# ============================================================
# 4. MAIN
# ============================================================

def main():
    start_total = time.time()

    print("=" * 60)
    print("CAGEMIND — SEMANA 1: FEATURE SELECTION + RE-ENTRENAMIENTO")
    print("=" * 60)

    # ── Cargar datos ──
    df = load_data()
    feature_cols = get_feature_columns(df)
    print(f"  Features iniciales: {len(feature_cols)}")

    # ── Feature Selection ──
    selected_features = feature_selection(df, feature_cols)

    # ── Preparar datos con features reducidas ──
    X_full = df[selected_features].values
    y_winner = df["target_winner"].values
    y_method = df["target_method"].values
    y_distance = df["target_goes_distance"].values
    y_round = df["target_round"].values

    # Masks para cada modelo
    mask_winner = ~pd.isna(y_winner)
    mask_method = np.array([m in ["ko", "sub", "dec"] for m in y_method])
    mask_finish = np.array([m in ["ko", "sub"] for m in y_method])

    all_results = {}

    # ══════════════════════════════════════════════════════════
    # MODELO 1: QUIÉN GANA (LogReg/XGBoost + Platt Scaling)
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("MODELO 1: QUIÉN GANA")
    print(f"{'='*60}")

    X1 = X_full[mask_winner]
    y1 = y_winner[mask_winner].astype(int)
    print(f"  Samples: {len(y1)} | Features: {len(selected_features)}")

    X1_train, X1_test, y1_train, y1_test = train_test_split(
        X1, y1, test_size=0.15, random_state=RANDOM_STATE, stratify=y1
    )

    # Optuna: probar LogReg, RF, XGBoost
    start = time.time()
    study1 = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
    )
    obj1 = create_multi_algo_objective(X1_train, y1_train, is_multiclass=False)
    study1.optimize(obj1, n_trials=N_TRIALS, show_progress_bar=True)
    elapsed1 = time.time() - start

    best1 = study1.best_trial
    print(f"\n  Tiempo: {elapsed1:.0f}s")
    print(f"  Mejor CV: {best1.value:.4f}")
    print(f"  Algoritmo: {best1.params.get('algorithm', '?')}")

    # Entrenar mejor modelo
    pipeline1 = build_best_pipeline(study1, is_multiclass=False)
    pipeline1.fit(X1_train, y1_train)

    # Evaluar sin calibrar
    y1_pred = pipeline1.predict(X1_test)
    y1_proba = pipeline1.predict_proba(X1_test)[:, 1]
    acc1_raw = accuracy_score(y1_test, y1_pred)
    brier1_raw = brier_score_loss(y1_test, y1_proba)
    print(f"  Test Accuracy (raw): {acc1_raw:.4f}")
    print(f"  Test Brier (raw): {brier1_raw:.4f}")

    # Aplicar Platt Scaling
    print("  Aplicando Platt Scaling...")
    cal_base = build_best_pipeline(study1, is_multiclass=False)
    winner_calibrated = CalibratedClassifierCV(cal_base, method="sigmoid", cv=5)
    winner_calibrated.fit(X1_train, y1_train)

    y1_cal_proba = winner_calibrated.predict_proba(X1_test)[:, 1]
    acc1_cal = accuracy_score(y1_test, (y1_cal_proba >= 0.5).astype(int))
    brier1_cal = brier_score_loss(y1_test, y1_cal_proba)
    print(f"  Test Accuracy (Platt): {acc1_cal:.4f}")
    print(f"  Test Brier (Platt): {brier1_cal:.4f}")

    # Entrenar final en todo (train+test) para producción
    winner_final_base = build_best_pipeline(study1, is_multiclass=False)
    winner_final = CalibratedClassifierCV(winner_final_base, method="sigmoid", cv=5)
    winner_final.fit(X1, y1)

    all_results["winner"] = {
        "algorithm": best1.params.get("algorithm", "?"),
        "cv_score": round(best1.value, 4),
        "test_accuracy_raw": round(acc1_raw, 4),
        "test_accuracy_platt": round(acc1_cal, 4),
        "test_brier_raw": round(brier1_raw, 4),
        "test_brier_platt": round(brier1_cal, 4),
        "best_params": best1.params,
        "time_seconds": round(elapsed1, 0),
    }

    # ══════════════════════════════════════════════════════════
    # MODELO 2: CÓMO GANA (XGBoost multiclase — plan lo pide)
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("MODELO 2: CÓMO GANA (XGBoost multiclase + Optuna)")
    print(f"{'='*60}")

    X2 = X_full[mask_method]
    y2_raw = y_method[mask_method]
    le = LabelEncoder()
    y2 = le.fit_transform(y2_raw)
    print(f"  Samples: {len(y2)} | Clases: {list(le.classes_)}")

    # Forzar XGBoost multiclase (el plan dice que LogReg no captura interacciones)
    start = time.time()
    study2 = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
    )
    obj2 = create_xgb_objective(X2, y2, is_multiclass=True)
    study2.optimize(obj2, n_trials=N_TRIALS, show_progress_bar=True)
    elapsed2 = time.time() - start

    best2 = study2.best_trial
    print(f"\n  Tiempo: {elapsed2:.0f}s")
    print(f"  Mejor CV (f1_weighted): {best2.value:.4f}")

    # Evaluar en test
    X2_train, X2_test, y2_train, y2_test = train_test_split(
        X2, y2, test_size=0.2, random_state=RANDOM_STATE, stratify=y2
    )
    pipeline2 = build_best_pipeline(study2, is_multiclass=True)
    pipeline2.fit(X2_train, y2_train)
    y2_pred = pipeline2.predict(X2_test)
    acc2 = accuracy_score(y2_test, y2_pred)
    f1_2 = f1_score(y2_test, y2_pred, average="weighted", zero_division=0)
    print(f"  Test Accuracy: {acc2:.4f}")
    print(f"  Test F1 weighted: {f1_2:.4f}")

    # Final en todo
    method_final = build_best_pipeline(study2, is_multiclass=True)
    method_final.fit(X2, y2)

    all_results["method"] = {
        "algorithm": "xgboost_multiclass",
        "cv_f1_weighted": round(best2.value, 4),
        "test_accuracy": round(acc2, 4),
        "test_f1_weighted": round(f1_2, 4),
        "best_params": best2.params,
        "time_seconds": round(elapsed2, 0),
    }

    # ══════════════════════════════════════════════════════════
    # MODELO 3: FINISH VS DECISIÓN
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("MODELO 3: FINISH VS DECISIÓN")
    print(f"{'='*60}")

    mask3 = ~pd.isna(y_distance)
    X3 = X_full[mask3]
    y3 = y_distance[mask3].astype(int)
    print(f"  Samples: {len(y3)}")

    start = time.time()
    study3 = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
    )
    obj3 = create_multi_algo_objective(X3, y3, is_multiclass=False)
    study3.optimize(obj3, n_trials=N_TRIALS, show_progress_bar=True)
    elapsed3 = time.time() - start

    best3 = study3.best_trial
    print(f"\n  Tiempo: {elapsed3:.0f}s")
    print(f"  Mejor CV: {best3.value:.4f}")
    print(f"  Algoritmo: {best3.params.get('algorithm', '?')}")

    X3_train, X3_test, y3_train, y3_test = train_test_split(
        X3, y3, test_size=0.2, random_state=RANDOM_STATE, stratify=y3
    )
    pipeline3 = build_best_pipeline(study3, is_multiclass=False)
    pipeline3.fit(X3_train, y3_train)
    acc3 = accuracy_score(y3_test, pipeline3.predict(X3_test))
    print(f"  Test Accuracy: {acc3:.4f}")

    distance_final = build_best_pipeline(study3, is_multiclass=False)
    distance_final.fit(X3, y3)

    all_results["distance"] = {
        "algorithm": best3.params.get("algorithm", "?"),
        "cv_score": round(best3.value, 4),
        "test_accuracy": round(acc3, 4),
        "best_params": best3.params,
        "time_seconds": round(elapsed3, 0),
    }

    # ══════════════════════════════════════════════════════════
    # MODELO 4: EN QUÉ ROUND
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("MODELO 4: EN QUÉ ROUND (solo finishes)")
    print(f"{'='*60}")

    X4 = X_full[mask_finish]
    y4_raw = y_round[mask_finish]
    valid4 = ~pd.isna(y4_raw)
    X4 = X4[valid4]
    y4 = y4_raw[valid4].astype(int)
    y4 = np.clip(y4, 1, 4)   # Agrupar R4 y R5
    y4 = y4 - 1               # Zero-index para XGBoost
    print(f"  Samples: {len(y4)} | Clases: {np.unique(y4)}")

    start = time.time()
    study4 = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=RANDOM_STATE)
    )
    obj4 = create_xgb_objective(X4, y4, is_multiclass=True)
    study4.optimize(obj4, n_trials=N_TRIALS, show_progress_bar=True)
    elapsed4 = time.time() - start

    best4 = study4.best_trial
    print(f"\n  Tiempo: {elapsed4:.0f}s")
    print(f"  Mejor CV (f1_weighted): {best4.value:.4f}")

    X4_train, X4_test, y4_train, y4_test = train_test_split(
        X4, y4, test_size=0.2, random_state=RANDOM_STATE, stratify=y4
    )
    pipeline4 = build_best_pipeline(study4, is_multiclass=True)
    pipeline4.fit(X4_train, y4_train)
    acc4 = accuracy_score(y4_test, pipeline4.predict(X4_test))
    print(f"  Test Accuracy: {acc4:.4f}")

    round_final = build_best_pipeline(study4, is_multiclass=True)
    round_final.fit(X4, y4)

    all_results["round"] = {
        "algorithm": "xgboost_multiclass",
        "cv_f1_weighted": round(best4.value, 4),
        "test_accuracy": round(acc4, 4),
        "best_params": best4.params,
        "time_seconds": round(elapsed4, 0),
    }

    # ══════════════════════════════════════════════════════════
    # GUARDAR TODO
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("GUARDANDO MODELOS")
    print(f"{'='*60}")

    # Backup del modelo anterior
    if MODELS_PATH.exists():
        backup = MODELS_PATH.with_suffix(".pkl.pre_semana1")
        shutil.copy2(MODELS_PATH, backup)
        print(f"  Backup: {backup}")

    # Construir imputer con features seleccionadas
    final_imputer = SimpleImputer(strategy="median")
    final_imputer.fit(df[selected_features])

    bundle = {
        "winner_model": winner_final,
        "method_model": method_final,
        "method_encoder": le,
        "distance_model": distance_final,
        "round_model": round_final,
        "feature_names": selected_features,
        "imputer": final_imputer,
        "winner_model_calibrated": True,
        "feature_selection_applied": True,
        "version": "semana1_v1",
    }

    with open(MODELS_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  Modelos: {MODELS_PATH}")

    with open(FEATURES_PATH, "w") as f:
        json.dump(selected_features, f, indent=2)
    print(f"  Features ({len(selected_features)}): {FEATURES_PATH}")

    # Resultados
    results_path = OUTPUT_DIR / "semana1_results.json"
    all_results["feature_selection"] = {
        "original_features": len(feature_cols),
        "selected_features": len(selected_features),
        "eliminated": len(feature_cols) - len(selected_features),
    }
    all_results["total_time_minutes"] = round((time.time() - start_total) / 60, 1)

    with open(results_path, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"  Resultados: {results_path}")

    # ══════════════════════════════════════════════════════════
    # RESUMEN COMPARATIVO
    # ══════════════════════════════════════════════════════════
    print(f"\n{'='*60}")
    print("RESUMEN — ANTES vs DESPUÉS (SEMANA 1)")
    print(f"{'='*60}")

    # Antes (del doc oficial)
    before = {
        "winner": {"acc": 64.79, "label": "Quién gana"},
        "method": {"acc": 53.18, "label": "Cómo gana"},
        "distance": {"acc": 57.95, "label": "Finish vs Dec"},
        "round": {"acc": 47.43, "label": "En qué round"},
    }

    for key in ["winner", "method", "distance", "round"]:
        old = before[key]["acc"]
        if key == "winner":
            new = all_results[key]["test_accuracy_platt"] * 100
        elif key in ["method", "round"]:
            new = all_results[key]["test_accuracy"] * 100
        else:
            new = all_results[key]["test_accuracy"] * 100

        diff = new - old
        arrow = "↑" if diff > 0 else "↓" if diff < 0 else "="
        algo = all_results[key]["algorithm"]
        print(f"  {before[key]['label']:18s}  {old:5.2f}% → {new:5.2f}%  ({arrow}{abs(diff):.2f}pp)  [{algo}]")

    feat_before = len(feature_cols)
    feat_after = len(selected_features)
    print(f"\n  Features: {feat_before} → {feat_after} ({feat_before - feat_after} eliminadas)")
    print(f"  Platt Scaling: ✅ (Brier {all_results['winner']['test_brier_raw']:.4f} → {all_results['winner']['test_brier_platt']:.4f})")
    print(f"  Tiempo total: {all_results['total_time_minutes']:.1f} minutos")

    print(f"\n{'='*60}")
    print("SIGUIENTE PASO:")
    print("  1. Hacer git add + commit + push")
    print("  2. Railway redeploya automáticamente")
    print("  3. Verificar en cagemind.vercel.app que las predicciones funcionan")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
