"""
CageMind — Merge Híbrido de Modelos

Combina los mejores modelos de cada fuente:
  - Winner (Semana 1): LogReg + Platt Scaling, 65.15% accuracy
  - Finish vs Dec (Semana 1): RF, 60.73% accuracy
  - Método (Tuning anterior): LogReg, 51.19% accuracy
  - Round (Tuning anterior): XGBoost, 44.46% accuracy

Uso:
    cd cagemind
    python merge_models.py
"""
from __future__ import annotations

import json
import pickle
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
MODELS_DIR = PROJECT_ROOT / "ml" / "models"

# Archivos de modelos
SEMANA1_PATH = MODELS_DIR / "ufc_predictor_models.pkl"        # Tiene winner + finish nuevos
TUNED_PATH = MODELS_DIR / "ufc_predictor_models_tuned.pkl"    # Tiene método + round mejores
OUTPUT_PATH = MODELS_DIR / "ufc_predictor_models.pkl"
FEATURES_PATH = MODELS_DIR / "feature_names.json"


def main():
    print("=" * 60)
    print("CAGEMIND — MERGE HÍBRIDO DE MODELOS")
    print("=" * 60)

    # Verificar que existan ambos archivos
    if not SEMANA1_PATH.exists():
        print(f"ERROR: No se encontró {SEMANA1_PATH}")
        return
    if not TUNED_PATH.exists():
        print(f"ERROR: No se encontró {TUNED_PATH}")
        print("Necesitas el archivo ufc_predictor_models_tuned.pkl del tuning anterior.")
        return

    # Cargar ambos bundles
    print("\nCargando modelos...")
    with open(SEMANA1_PATH, "rb") as f:
        semana1 = pickle.load(f)

    with open(TUNED_PATH, "rb") as f:
        tuned = pickle.load(f)

    print(f"  Semana 1 keys: {list(semana1.keys())}")
    print(f"  Tuned keys: {list(tuned.keys())}")

    # Verificar features
    s1_features = semana1.get("feature_names", [])
    tuned_features = tuned.get("feature_names", [])
    print(f"\n  Semana 1 features: {len(s1_features)}")
    print(f"  Tuned features: {len(tuned_features)}")

    # Los modelos tuned usan 167 features, los de semana1 usan 146
    # Necesitamos que TODOS los modelos usen las mismas features
    # Opción: usar las 146 de semana1 (es un subset de las 167)
    # Los modelos tuned tienen pipelines con imputer+scaler, así que
    # necesitamos re-entrenar método y round con las 146 features...
    # PERO eso requiere el dataset.
    #
    # Alternativa más simple: usar las 167 features del tuned para TODO
    # y solo reemplazar winner y finish con los de semana1.
    # Pero semana1 winner/finish fueron entrenados con 146 features.
    #
    # Solución correcta: usar las 146 features de semana1 para winner
    # y finish, y las 167 del tuned para método y round.
    # Esto requiere que app.py use el feature set correcto por modelo.
    #
    # Solución PRAGMÁTICA: mantener los 167 features como feature_names
    # global, y re-entrenar winner+finish con 167 features.
    # Pero eso pierde la mejora del feature selection...
    #
    # MEJOR SOLUCIÓN: Los modelos tuned son Pipelines con
    # imputer+scaler+model. Si les pasamos 146 features en vez de 167,
    # van a fallar. Pero podemos construir un wrapper.
    #
    # La solución MÁS LIMPIA es re-entrenar método y round con las
    # 146 features. Es rápido (~2 min) usando los mejores params
    # del tuning anterior.

    print("\n" + "=" * 60)
    print("Re-entrenando método y round con 146 features...")
    print("(usando los mejores hyperparams del tuning anterior)")
    print("=" * 60)

    import numpy as np
    import pandas as pd
    from sklearn.impute import SimpleImputer
    from sklearn.preprocessing import StandardScaler, LabelEncoder
    from sklearn.pipeline import Pipeline
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score

    try:
        from xgboost import XGBClassifier
    except ImportError:
        from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier

    # Cargar dataset
    dataset_path = PROJECT_ROOT / "data" / "processed" / "training_dataset_v2.csv"
    if not dataset_path.exists():
        dataset_path = PROJECT_ROOT / "data" / "processed" / "training_dataset.csv"
    df = pd.read_csv(dataset_path)
    print(f"  Dataset: {len(df)} peleas")

    # Usar las 146 features de semana1
    features = s1_features
    X_full = df[features].values
    y_method = df["target_method"].values
    y_round = df["target_round"].values

    # Cargar mejores params del tuning anterior
    tuning_results_path = MODELS_DIR / "tuning_results.json"
    with open(tuning_results_path) as f:
        tuning_results = json.load(f)

    # ── MODELO 2: Método ──
    print("\n  Modelo 2 (Método): re-entrenando con LogReg...")
    mask_method = np.array([m in ["ko", "sub", "dec"] for m in y_method])
    X2 = X_full[mask_method]
    y2_raw = y_method[mask_method]
    le = LabelEncoder()
    y2 = le.fit_transform(y2_raw)

    method_params = tuning_results["method"]["best_params"]
    method_model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            C=method_params["lr_C"],
            penalty=method_params.get("lr_penalty", "l2"),
            solver=method_params.get("lr_solver", "lbfgs"),
            max_iter=2000, random_state=42,
            multi_class="multinomial",
        )),
    ])

    X2_train, X2_test, y2_train, y2_test = train_test_split(
        X2, y2, test_size=0.2, random_state=42, stratify=y2
    )
    method_model.fit(X2_train, y2_train)
    acc2 = accuracy_score(y2_test, method_model.predict(X2_test))
    print(f"    Test Accuracy: {acc2:.4f}")

    # Fit final en todo
    method_final = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            C=method_params["lr_C"],
            penalty=method_params.get("lr_penalty", "l2"),
            solver=method_params.get("lr_solver", "lbfgs"),
            max_iter=2000, random_state=42,
            multi_class="multinomial",
        )),
    ])
    method_final.fit(X2, y2)

    # ── MODELO 4: Round ──
    print("\n  Modelo 4 (Round): re-entrenando con XGBoost...")
    mask_finish = np.array([m in ["ko", "sub"] for m in y_method])
    X4 = X_full[mask_finish]
    y4_raw = y_round[mask_finish]
    valid4 = ~pd.isna(y4_raw)
    X4 = X4[valid4]
    y4 = y4_raw[valid4].astype(int)
    y4 = np.clip(y4, 1, 4)
    y4 = y4 - 1  # zero-index

    round_params = tuning_results["round"]["best_params"]
    round_model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", XGBClassifier(
            n_estimators=round_params["xgb_n_estimators"],
            max_depth=round_params["xgb_max_depth"],
            learning_rate=round_params["xgb_learning_rate"],
            subsample=round_params["xgb_subsample"],
            colsample_bytree=round_params["xgb_colsample_bytree"],
            reg_alpha=round_params["xgb_reg_alpha"],
            reg_lambda=round_params["xgb_reg_lambda"],
            min_child_weight=round_params["xgb_min_child_weight"],
            gamma=round_params["xgb_gamma"],
            random_state=42,
            eval_metric="mlogloss",
            verbosity=0, n_jobs=-1,
        )),
    ])

    X4_train, X4_test, y4_train, y4_test = train_test_split(
        X4, y4, test_size=0.2, random_state=42, stratify=y4
    )
    round_model.fit(X4_train, y4_train)
    acc4 = accuracy_score(y4_test, round_model.predict(X4_test))
    print(f"    Test Accuracy: {acc4:.4f}")

    round_final = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", XGBClassifier(
            n_estimators=round_params["xgb_n_estimators"],
            max_depth=round_params["xgb_max_depth"],
            learning_rate=round_params["xgb_learning_rate"],
            subsample=round_params["xgb_subsample"],
            colsample_bytree=round_params["xgb_colsample_bytree"],
            reg_alpha=round_params["xgb_reg_alpha"],
            reg_lambda=round_params["xgb_reg_lambda"],
            min_child_weight=round_params["xgb_min_child_weight"],
            gamma=round_params["xgb_gamma"],
            random_state=42,
            eval_metric="mlogloss",
            verbosity=0, n_jobs=-1,
        )),
    ])
    round_final.fit(X4, y4)

    # ══════════════════════════════════════════════════════════
    # ARMAR BUNDLE HÍBRIDO
    # ══════════════════════════════════════════════════════════
    print("\n" + "=" * 60)
    print("ARMANDO BUNDLE HÍBRIDO")
    print("=" * 60)

    # Backup
    backup = OUTPUT_PATH.with_suffix(".pkl.pre_merge")
    shutil.copy2(OUTPUT_PATH, backup)
    print(f"  Backup: {backup}")

    hybrid = {
        "winner_model": semana1["winner_model"],           # Semana 1 (Platt)
        "method_model": method_final,                       # Tuning params + 146 features
        "method_encoder": le,                               # Fresh LabelEncoder
        "distance_model": semana1["distance_model"],        # Semana 1 (RF)
        "round_model": round_final,                         # Tuning params + 146 features
        "feature_names": features,                          # 146 features
        "imputer": semana1.get("imputer"),                  # Imputer de semana1
        "winner_model_calibrated": True,
        "feature_selection_applied": True,
        "version": "semana1_hybrid",
    }

    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(hybrid, f)
    print(f"  Modelo híbrido guardado: {OUTPUT_PATH}")

    with open(FEATURES_PATH, "w") as f:
        json.dump(features, f, indent=2)
    print(f"  Features ({len(features)}): {FEATURES_PATH}")

    # Resumen
    print(f"\n{'='*60}")
    print("RESUMEN BUNDLE HÍBRIDO")
    print(f"{'='*60}")
    print(f"  Winner:      Semana 1 (LogReg + Platt)  65.15%")
    print(f"  Método:      Tuning (LogReg refit)      {acc2*100:.2f}%")
    print(f"  Finish/Dec:  Semana 1 (RF)              60.73%")
    print(f"  Round:       Tuning (XGBoost refit)     {acc4*100:.2f}%")
    print(f"  Features:    {len(features)} (146)")
    print(f"  Platt:       ✅")
    print(f"\nSIGUIENTE:")
    print(f"  1. git add + commit + push")
    print(f"  2. Verificar en producción")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
