"""
UFC Fight Predictor — Fase 4: Modelo Predictivo

Entrena 4 modelos en capas:
  Modelo 1: ¿Quién gana? (clasificación binaria)
  Modelo 2: ¿Cómo gana? (KO, Sub, Decisión — multiclase)
  Modelo 3: ¿Llega a decisión? (clasificación binaria)
  Modelo 4: ¿En qué round termina? (regresión/clasificación)

Para cada modelo:
  1. Baseline con Logistic Regression
  2. Random Forest
  3. XGBoost (si disponible)
  4. Cross-validation con 5 folds
  5. Evaluación: accuracy, precision, recall, F1, ROC-AUC

Uso:
    python -m pip install scikit-learn xgboost
    python run_phase4_model.py
"""
from __future__ import annotations

import json
import pickle
import warnings
from pathlib import Path

import pandas as pd
import numpy as np

from sklearn.model_selection import cross_val_score, StratifiedKFold, train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)

warnings.filterwarnings("ignore")

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    print("NOTA: xgboost no instalado. Instalar con: python -m pip install xgboost")
    print("      Continuando sin XGBoost...\n")

DATA_PATH = Path("data/processed/training_dataset.csv")
MODEL_DIR = Path("ml/models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR = Path("ml/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# PREPARACIÓN DE DATOS
# ============================================================

def load_and_prepare():
    """Carga el dataset y prepara features y targets."""
    print("Cargando dataset...")
    df = pd.read_csv(DATA_PATH)
    print("  Shape: " + str(df.shape))

    # Excluir columnas no-feature
    meta_cols = ["fight_id", "date", "fighter_a", "fighter_b", "weight_class",
                 "target_winner", "target_method", "target_round", "target_goes_distance",
                 "a_last_weight_class", "b_last_weight_class"]

    # Excluir cardio_ratio (100% nulo)
    drop_cols = [c for c in df.columns if "cardio_ratio" in c]

    feature_cols = [c for c in df.columns if c not in meta_cols and c not in drop_cols]

    # Solo features numéricas
    X = df[feature_cols].select_dtypes(include=[np.number]).copy()
    feature_names = list(X.columns)

    print("  Features numéricas: " + str(len(feature_names)))
    print("  Excluidas (cardio_ratio): " + str(len(drop_cols)))

    # Targets
    y_winner = df["target_winner"].values
    y_method = df["target_method"].values
    y_distance = df["target_goes_distance"].values
    y_round = df["target_round"].values

    return df, X, feature_names, y_winner, y_method, y_distance, y_round


def build_pipeline(model, impute_strategy="median"):
    """Construye pipeline con imputación + escalado + modelo."""
    return Pipeline([
        ("imputer", SimpleImputer(strategy=impute_strategy)),
        ("scaler", StandardScaler()),
        ("model", model),
    ])


def evaluate_model(name, pipeline, X, y, cv=5, is_multiclass=False):
    """Evalúa un modelo con cross-validation y retorna métricas."""
    skf = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

    # Cross-validation scores
    acc_scores = cross_val_score(pipeline, X, y, cv=skf, scoring="accuracy")
    f1_avg = "weighted" if is_multiclass else "binary"
    f1_scoring = "f1_weighted" if is_multiclass else "f1"
    f1_scores = cross_val_score(pipeline, X, y, cv=skf, scoring=f1_scoring)

    result = {
        "name": name,
        "cv_accuracy_mean": round(acc_scores.mean(), 4),
        "cv_accuracy_std": round(acc_scores.std(), 4),
        "cv_f1_mean": round(f1_scores.mean(), 4),
        "cv_f1_std": round(f1_scores.std(), 4),
    }

    # Train/test split para métricas detalladas
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    result["test_accuracy"] = round(accuracy_score(y_test, y_pred), 4)

    if not is_multiclass:
        result["test_precision"] = round(precision_score(y_test, y_pred, zero_division=0), 4)
        result["test_recall"] = round(recall_score(y_test, y_pred, zero_division=0), 4)
        result["test_f1"] = round(f1_score(y_test, y_pred, zero_division=0), 4)
        if hasattr(pipeline, "predict_proba"):
            try:
                y_proba = pipeline.predict_proba(X_test)[:, 1]
                result["test_roc_auc"] = round(roc_auc_score(y_test, y_proba), 4)
            except Exception:
                result["test_roc_auc"] = None
    else:
        result["test_precision"] = round(precision_score(y_test, y_pred, average="weighted", zero_division=0), 4)
        result["test_recall"] = round(recall_score(y_test, y_pred, average="weighted", zero_division=0), 4)
        result["test_f1"] = round(f1_score(y_test, y_pred, average="weighted", zero_division=0), 4)

    return result, pipeline


def print_results(results):
    """Imprime resultados de forma legible."""
    print("  " + "-" * 75)
    print("  {:<25s} {:>8s} {:>8s} {:>8s} {:>8s} {:>8s}".format(
        "Modelo", "CV Acc", "CV F1", "Test Acc", "Test F1", "ROC-AUC"))
    print("  " + "-" * 75)
    for r in results:
        roc = str(r.get("test_roc_auc", "-")) if r.get("test_roc_auc") else "-"
        print("  {:<25s} {:>8s} {:>8s} {:>8s} {:>8s} {:>8s}".format(
            r["name"],
            str(r["cv_accuracy_mean"]) + "+-" + str(r["cv_accuracy_std"]),
            str(r["cv_f1_mean"]),
            str(r["test_accuracy"]),
            str(r["test_f1"]),
            roc
        ))
    print("  " + "-" * 75)


def get_feature_importance(pipeline, feature_names, top_n=20):
    """Extrae feature importance del modelo dentro del pipeline."""
    model = pipeline.named_steps["model"]
    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    elif hasattr(model, "coef_"):
        importances = np.abs(model.coef_).flatten() if model.coef_.ndim == 1 else np.abs(model.coef_).mean(axis=0)
    else:
        return None

    fi = pd.Series(importances, index=feature_names).sort_values(ascending=False)
    return fi.head(top_n)


# ============================================================
# MODELO 1: ¿QUIÉN GANA?
# ============================================================
def train_winner_model(X, y, feature_names):
    print("\n" + "=" * 60)
    print("MODELO 1: QUIEN GANA (Clasificacion Binaria)")
    print("=" * 60)
    print("  Samples: " + str(len(y)) + " | Positivos: " + str(sum(y)) + " | Negativos: " + str(len(y) - sum(y)))
    print()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, C=1.0, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=10, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, random_state=42,
                                           use_label_encoder=False, eval_metric="logloss", verbosity=0)

    results = []
    best_score = 0
    best_pipeline = None
    best_name = ""

    for name, model in models.items():
        print("  Entrenando " + name + "...")
        pipeline = build_pipeline(model)
        result, fitted_pipeline = evaluate_model(name, pipeline, X, y)
        results.append(result)

        score = result["cv_accuracy_mean"]
        if score > best_score:
            best_score = score
            best_pipeline = fitted_pipeline
            best_name = name

    print()
    print_results(results)

    print("\n  Mejor modelo: " + best_name + " (CV Accuracy: " + str(best_score) + ")")

    # Feature importance del mejor modelo
    # Reentrenar en todo el dataset
    final_pipeline = build_pipeline(models[best_name])
    final_pipeline.fit(X, y)

    fi = get_feature_importance(final_pipeline, feature_names)
    if fi is not None:
        print("\n  Top 20 features mas importantes:")
        for feat, imp in fi.items():
            print("    " + feat + ": " + str(round(imp, 4)))

    return final_pipeline, results, best_name


# ============================================================
# MODELO 2: ¿CÓMO GANA? (KO, Sub, Dec)
# ============================================================
def train_method_model(X, y_method, feature_names):
    print("\n" + "=" * 60)
    print("MODELO 2: COMO GANA (Clasificacion Multiclase)")
    print("=" * 60)

    # Filtrar 'other' (solo 11 peleas)
    mask = np.array([m in ["ko", "sub", "dec"] for m in y_method])
    X_m = X[mask]
    y_m = y_method[mask]

    le = LabelEncoder()
    y_encoded = le.fit_transform(y_m)
    print("  Classes: " + str(list(le.classes_)))
    print("  Distribution: " + str(dict(zip(le.classes_, np.bincount(y_encoded)))))
    print()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, multi_class="multinomial", random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=10, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, random_state=42,
                                           use_label_encoder=False, eval_metric="mlogloss", verbosity=0)

    results = []
    best_score = 0
    best_name = ""

    for name, model in models.items():
        print("  Entrenando " + name + "...")
        pipeline = build_pipeline(model)
        result, _ = evaluate_model(name, pipeline, X_m, y_encoded, is_multiclass=True)
        results.append(result)

        if result["cv_accuracy_mean"] > best_score:
            best_score = result["cv_accuracy_mean"]
            best_name = name

    print()
    print_results(results)
    print("\n  Mejor modelo: " + best_name + " (CV Accuracy: " + str(best_score) + ")")

    # Entrenar final
    final_pipeline = build_pipeline(models[best_name])
    final_pipeline.fit(
        SimpleImputer(strategy="median").fit_transform(X_m),
        y_encoded
    )

    # Reentrenar pipeline completo
    final_pipeline = build_pipeline(models[best_name])
    final_pipeline.fit(X_m, y_encoded)

    return final_pipeline, le, results, best_name


# ============================================================
# MODELO 3: ¿LLEGA A DECISIÓN?
# ============================================================
def train_distance_model(X, y_distance, feature_names):
    print("\n" + "=" * 60)
    print("MODELO 3: LLEGA A DECISION? (Clasificacion Binaria)")
    print("=" * 60)
    print("  Decision: " + str(sum(y_distance)) + " | Finish: " + str(len(y_distance) - sum(y_distance)))
    print()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=12, min_samples_leaf=10, random_state=42, n_jobs=-1),
        "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(n_estimators=300, max_depth=6, learning_rate=0.1, random_state=42,
                                           use_label_encoder=False, eval_metric="logloss", verbosity=0)

    results = []
    best_score = 0
    best_name = ""

    for name, model in models.items():
        print("  Entrenando " + name + "...")
        pipeline = build_pipeline(model)
        result, _ = evaluate_model(name, pipeline, X, y_distance)
        results.append(result)

        if result["cv_accuracy_mean"] > best_score:
            best_score = result["cv_accuracy_mean"]
            best_name = name

    print()
    print_results(results)
    print("\n  Mejor modelo: " + best_name + " (CV Accuracy: " + str(best_score) + ")")

    final_pipeline = build_pipeline(models[best_name])
    final_pipeline.fit(X, y_distance)

    return final_pipeline, results, best_name


# ============================================================
# MODELO 4: ¿EN QUÉ ROUND?
# ============================================================
def train_round_model(X, y_method, y_round, feature_names):
    print("\n" + "=" * 60)
    print("MODELO 4: EN QUE ROUND TERMINA (Solo finishes)")
    print("=" * 60)

    # Solo peleas que terminaron en finish (no decisión)
    mask = np.array([m in ["ko", "sub"] for m in y_method])
    X_r = X[mask]
    y_r = y_round[mask]

    # Limpiar nulos en target
    valid = ~pd.isna(y_r)
    X_r = X_r[valid]
    y_r = y_r[valid].astype(int)

    # Agrupar rounds 4-5 como "late" para tener suficientes samples
    y_r_grouped = y_r.copy()
    y_r_grouped[y_r_grouped >= 4] = 4
    y_r_grouped = y_r_grouped - 1  # Shift a 0-indexed: [0,1,2,3]

    print("  Finishes: " + str(len(y_r)))
    print("  Distribution: " + str(dict(zip(*np.unique(y_r_grouped, return_counts=True)))))
    print()

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000, multi_class="multinomial", random_state=42),
        "Random Forest": RandomForestClassifier(n_estimators=200, max_depth=10, min_samples_leaf=10, random_state=42, n_jobs=-1),
    }

    if HAS_XGBOOST:
        models["XGBoost"] = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42,
                                           use_label_encoder=False, eval_metric="mlogloss", verbosity=0)

    results = []
    best_score = 0
    best_name = ""

    for name, model in models.items():
        print("  Entrenando " + name + "...")
        pipeline = build_pipeline(model)
        result, _ = evaluate_model(name, pipeline, X_r, y_r_grouped, is_multiclass=True)
        results.append(result)

        if result["cv_accuracy_mean"] > best_score:
            best_score = result["cv_accuracy_mean"]
            best_name = name

    print()
    print_results(results)
    print("\n  Mejor modelo: " + best_name + " (CV Accuracy: " + str(best_score) + ")")

    final_pipeline = build_pipeline(models[best_name])
    final_pipeline.fit(X_r, y_r_grouped)

    return final_pipeline, results, best_name


# ============================================================
# GUARDAR MODELOS
# ============================================================
def save_models(winner_model, method_model, method_encoder, distance_model, round_model, feature_names):
    """Guarda todos los modelos entrenados."""
    print("\nGuardando modelos...")

    models_bundle = {
        "winner_model": winner_model,
        "method_model": method_model,
        "method_encoder": method_encoder,
        "distance_model": distance_model,
        "round_model": round_model,
        "feature_names": feature_names,
    }

    bundle_path = MODEL_DIR / "ufc_predictor_models.pkl"
    with open(bundle_path, "wb") as f:
        pickle.dump(models_bundle, f)
    print("  Bundle guardado: " + str(bundle_path))

    # Guardar feature names por separado
    with open(MODEL_DIR / "feature_names.json", "w") as f:
        json.dump(feature_names, f, indent=2)
    print("  Feature names: " + str(MODEL_DIR / "feature_names.json"))


# ============================================================
# MAIN
# ============================================================
def main():
    print("=" * 60)
    print("UFC FIGHT PREDICTOR - FASE 4: MODELO PREDICTIVO")
    print("=" * 60)

    df, X, feature_names, y_winner, y_method, y_distance, y_round = load_and_prepare()

    X_values = X.values

    # Entrenar modelos
    winner_pipeline, winner_results, winner_best = train_winner_model(X_values, y_winner, feature_names)
    method_pipeline, method_encoder, method_results, method_best = train_method_model(X_values, y_method, feature_names)
    distance_pipeline, distance_results, distance_best = train_distance_model(X_values, y_distance, feature_names)
    round_pipeline, round_results, round_best = train_round_model(X_values, y_method, y_round, feature_names)

    # Guardar modelos
    save_models(winner_pipeline, method_pipeline, method_encoder,
                distance_pipeline, round_pipeline, feature_names)

    # Guardar resultados
    all_results = {
        "winner": {"best": winner_best, "results": winner_results},
        "method": {"best": method_best, "results": method_results},
        "distance": {"best": distance_best, "results": distance_results},
        "round": {"best": round_best, "results": round_results},
    }
    with open(RESULTS_DIR / "training_results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    # Resumen final
    print("\n" + "=" * 60)
    print("RESUMEN FINAL")
    print("=" * 60)
    print("  Modelo 1 (Quien gana):       " + winner_best + " - " + str(winner_results[-1]["cv_accuracy_mean"] if winner_best == winner_results[-1]["name"] else [r for r in winner_results if r["name"] == winner_best][0]["cv_accuracy_mean"]))
    print("  Modelo 2 (Como gana):         " + method_best + " - " + str([r for r in method_results if r["name"] == method_best][0]["cv_accuracy_mean"]))
    print("  Modelo 3 (Llega a decision):  " + distance_best + " - " + str([r for r in distance_results if r["name"] == distance_best][0]["cv_accuracy_mean"]))
    print("  Modelo 4 (En que round):      " + round_best + " - " + str([r for r in round_results if r["name"] == round_best][0]["cv_accuracy_mean"]))
    print()
    print("  Modelos guardados en: " + str(MODEL_DIR.absolute()))
    print("  Resultados en: " + str(RESULTS_DIR.absolute()))
    print()
    print("=" * 60)
    print("FASE 4 COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    main()