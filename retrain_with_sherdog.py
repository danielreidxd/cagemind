

"""
Re-entrenar modelo CageMind con features de Sherdog integradas.
1. Carga training_dataset.csv existente
2. Mergea features pre-UFC de sherdog_features
3. Re-entrena los 4 modelos
4. Compara accuracy antes vs después

Uso: python retrain_with_sherdog.py
"""
from __future__ import annotations

import json
import pickle
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.impute import SimpleImputer

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False
    print("XGBoost no disponible, usando GradientBoosting como reemplazo")

DB_PATH = Path("db/ufc_predictor.db")
DATASET_PATH = Path("data/processed/training_dataset.csv")
MODELS_PATH = Path("ml/models/ufc_predictor_models.pkl")
FEATURES_PATH = Path("ml/models/feature_names.json")
RESULTS_PATH = Path("ml/results/training_results_v2.json")

SHERDOG_FEATURES = [
    "pre_ufc_fights", "pre_ufc_wr", "pre_ufc_ko_rate", "pre_ufc_sub_rate",
    "pre_ufc_dec_rate", "pre_ufc_finish_rate", "pre_ufc_ko_loss_rate",
    "pre_ufc_sub_loss_rate", "pre_ufc_streak", "total_pro_fights", "org_level",
]


def load_sherdog_features():
    """Cargar features de Sherdog desde la BD."""
    conn = sqlite3.connect(str(DB_PATH))
    df = pd.read_sql("SELECT * FROM sherdog_features", conn)
    conn.close()
    print(f"Sherdog features cargadas: {len(df)} peleadores")
    return df.set_index("name")


def merge_sherdog_to_dataset(df, sherdog_df):
    """Mergear features de Sherdog al training dataset."""
    print(f"\nDataset original: {df.shape[0]} peleas, {df.shape[1]} columnas")

    # Para cada pelea, agregar features pre-UFC de ambos peleadores
    for feat in SHERDOG_FEATURES:
        # Fighter A
        col_a = "a_" + feat
        df[col_a] = df["fighter_a"].map(
            sherdog_df[feat] if feat in sherdog_df.columns else pd.Series(dtype=float)
        )

        # Fighter B
        col_b = "b_" + feat
        df[col_b] = df["fighter_b"].map(
            sherdog_df[feat] if feat in sherdog_df.columns else pd.Series(dtype=float)
        )

        # Diferencial
        col_d = "diff_" + feat
        df[col_d] = df[col_a].fillna(0) - df[col_b].fillna(0)

    # Rellenar NaN con 0 para peleadores sin datos Sherdog
    new_cols = []
    for feat in SHERDOG_FEATURES:
        new_cols.extend(["a_" + feat, "b_" + feat, "diff_" + feat])

    for col in new_cols:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    print(f"Dataset con Sherdog: {df.shape[0]} peleas, {df.shape[1]} columnas")
    print(f"Nuevas features: {len(new_cols)}")

    # Stats de cobertura
    has_a = (df["a_pre_ufc_fights"] > 0).sum()
    has_b = (df["b_pre_ufc_fights"] > 0).sum()
    has_both = ((df["a_pre_ufc_fights"] > 0) & (df["b_pre_ufc_fights"] > 0)).sum()
    print(f"Peleas con datos Sherdog para A: {has_a} ({has_a/len(df)*100:.1f}%)")
    print(f"Peleas con datos Sherdog para B: {has_b} ({has_b/len(df)*100:.1f}%)")
    print(f"Peleas con datos para ambos: {has_both} ({has_both/len(df)*100:.1f}%)")

    return df, new_cols


def get_feature_columns(df, new_cols):
    """Obtener lista de feature columns (excluyendo targets y metadata)."""
    exclude = {
        "fighter_a", "fighter_b", "fight_id", "event_id", "date",
        "target_winner", "target_method", "target_round",
        "target_goes_distance", "weight_class",
    }
    # Solo columnas numéricas
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    feature_cols = [c for c in numeric_cols if c not in exclude]
    return feature_cols


def train_models(df, feature_cols):
    """Entrenar los 4 modelos con el dataset mejorado."""
    results = {}

    # Preparar datos
    X = df[feature_cols].copy()

    # Imputar NaN
    # Eliminar columnas 100% nulas
    all_null = X.columns[X.isnull().all()].tolist()
    if all_null:
        print(f"  Eliminando {len(all_null)} columnas 100% nulas: {all_null}")
        X = X.drop(columns=all_null)
        feature_cols = [c for c in feature_cols if c not in all_null]

    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(imputer.fit_transform(X), columns=feature_cols, index=X.index)

    # ================================================
    # MODELO 1: Quién gana
    # ================================================
    print("\n" + "=" * 50)
    print("MODELO 1: Quien gana (clasificacion binaria)")
    print("=" * 50)

    y1 = df["target_winner"]
    mask1 = y1.notna()
    X1 = X_imputed[mask1]
    y1 = y1[mask1].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(X1, y1, test_size=0.2, random_state=42)

    # Logistic Regression
    lr = LogisticRegression(max_iter=2000, random_state=42, C=0.5)
    lr_cv = cross_val_score(lr, X_train, y_train, cv=5, scoring="accuracy")
    lr.fit(X_train, y_train)
    lr_test = lr.score(X_test, y_test)
    print(f"  Logistic Regression: CV={lr_cv.mean():.4f}, Test={lr_test:.4f}")

    # XGBoost / GradientBoosting
    if HAS_XGB:
        xgb = XGBClassifier(n_estimators=200, max_depth=5, learning_rate=0.1,
                            random_state=42, eval_metric="logloss", verbosity=0)
    else:
        xgb = GradientBoostingClassifier(n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42)

    xgb_cv = cross_val_score(xgb, X_train, y_train, cv=5, scoring="accuracy")
    xgb.fit(X_train, y_train)
    xgb_test = xgb.score(X_test, y_test)
    print(f"  XGBoost:             CV={xgb_cv.mean():.4f}, Test={xgb_test:.4f}")

    # Elegir mejor
    if xgb_test > lr_test:
        winner_model = xgb
        print(f"  >> Mejor: XGBoost ({xgb_test:.4f})")
    else:
        winner_model = lr
        print(f"  >> Mejor: Logistic Regression ({lr_test:.4f})")

    results["model1"] = {"lr_cv": lr_cv.mean(), "lr_test": lr_test, "xgb_cv": xgb_cv.mean(), "xgb_test": xgb_test}

    # ================================================
    # MODELO 2: Cómo gana
    # ================================================
    print("\n" + "=" * 50)
    print("MODELO 2: Como gana (KO/Sub/Dec)")
    print("=" * 50)

    y2 = df["target_method"]
    mask2 = y2.notna()
    X2 = X_imputed[mask2]
    y2 = y2[mask2]

    le = LabelEncoder()
    y2_enc = le.fit_transform(y2)

    X2_train, X2_test, y2_train, y2_test = train_test_split(X2, y2_enc, test_size=0.2, random_state=42)

    rf_method = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    rf_method_cv = cross_val_score(rf_method, X2_train, y2_train, cv=5, scoring="accuracy")
    rf_method.fit(X2_train, y2_train)
    rf_method_test = rf_method.score(X2_test, y2_test)
    print(f"  Random Forest: CV={rf_method_cv.mean():.4f}, Test={rf_method_test:.4f}")

    results["model2"] = {"cv": rf_method_cv.mean(), "test": rf_method_test}

    # ================================================
    # MODELO 3: Llega a decisión
    # ================================================
    print("\n" + "=" * 50)
    print("MODELO 3: Llega a decision vs Finish")
    print("=" * 50)

    y3 = df["target_goes_distance"]
    mask3 = y3.notna()
    X3 = X_imputed[mask3]
    y3 = y3[mask3].astype(int)

    X3_train, X3_test, y3_train, y3_test = train_test_split(X3, y3, test_size=0.2, random_state=42)

    rf_dist = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    rf_dist_cv = cross_val_score(rf_dist, X3_train, y3_train, cv=5, scoring="accuracy")
    rf_dist.fit(X3_train, y3_train)
    rf_dist_test = rf_dist.score(X3_test, y3_test)
    print(f"  Random Forest: CV={rf_dist_cv.mean():.4f}, Test={rf_dist_test:.4f}")

    results["model3"] = {"cv": rf_dist_cv.mean(), "test": rf_dist_test}

    # ================================================
    # MODELO 4: En qué round
    # ================================================
    print("\n" + "=" * 50)
    print("MODELO 4: En que round (solo finishes)")
    print("=" * 50)

    y4 = df["target_round"]
    mask4 = y4.notna() & (df["target_goes_distance"] == 0)
    X4 = X_imputed[mask4]
    y4 = y4[mask4].astype(int)

    # Agrupar R4 y R5
    y4 = y4.clip(upper=4)
    if HAS_XGB:
        y4_xgb = y4 - 1  # XGBoost necesita 0-indexed

    X4_train, X4_test, y4_train, y4_test = train_test_split(X4, y4, test_size=0.2, random_state=42)

    rf_round = RandomForestClassifier(n_estimators=200, max_depth=8, random_state=42)
    rf_round_cv = cross_val_score(rf_round, X4_train, y4_train, cv=5, scoring="accuracy")
    rf_round.fit(X4_train, y4_train)
    rf_round_test = rf_round.score(X4_test, y4_test)
    print(f"  Random Forest: CV={rf_round_cv.mean():.4f}, Test={rf_round_test:.4f}")

    results["model4"] = {"cv": rf_round_cv.mean(), "test": rf_round_test}

    return {
        "winner_model": winner_model,
        "method_model": rf_method,
        "method_encoder": le,
        "distance_model": rf_dist,
        "round_model": rf_round,
        "feature_names": feature_cols,
        "imputer": imputer,
    }, results


def main():
    print("=" * 60)
    print("CAGEMIND - RE-ENTRENAMIENTO CON DATOS SHERDOG")
    print("=" * 60)

    # Cargar datos
    print("\nCargando dataset original...")
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset: {len(df)} peleas")

    sherdog_df = load_sherdog_features()

    # Cargar resultados anteriores para comparar
    old_results = None
    old_results_path = Path("ml/results/training_results.json")
    if old_results_path.exists():
        with open(old_results_path) as f:
            old_results = json.load(f)

    # Merge Sherdog features
    df, new_cols = merge_sherdog_to_dataset(df, sherdog_df)

    # Feature columns
    feature_cols = get_feature_columns(df, new_cols)
    print(f"\nTotal features: {len(feature_cols)}")

    # Entrenar
    bundle, results = train_models(df, feature_cols)

    # Guardar modelos
    print("\n" + "=" * 50)
    print("GUARDANDO MODELOS")
    print("=" * 50)

    # Backup del modelo anterior
    if MODELS_PATH.exists():
        backup = MODELS_PATH.with_suffix(".pkl.bak")
        import shutil
        shutil.copy2(MODELS_PATH, backup)
        print(f"  Backup modelo anterior: {backup}")

    with open(MODELS_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  Modelos guardados: {MODELS_PATH}")

    with open(FEATURES_PATH, "w") as f:
        json.dump(bundle["feature_names"], f)
    print(f"  Features guardadas: {FEATURES_PATH} ({len(bundle['feature_names'])} features)")

    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Resultados: {RESULTS_PATH}")

    # Guardar dataset mejorado
    improved_path = Path("data/processed/training_dataset_v2.csv")
    df.to_csv(improved_path, index=False)
    print(f"  Dataset mejorado: {improved_path}")

    # Comparación
    print("\n" + "=" * 60)
    print("COMPARACION: ANTES vs DESPUES")
    print("=" * 60)

    m1 = results["model1"]
    best_old_test = 0
    if old_results:
        # Intentar extraer accuracy anterior
        for model_key in old_results:
            if isinstance(old_results[model_key], dict):
                for algo_key in old_results[model_key]:
                    if isinstance(old_results[model_key][algo_key], dict):
                        test_acc = old_results[model_key][algo_key].get("test_accuracy", 0)
                        if test_acc > best_old_test:
                            best_old_test = test_acc

    best_new_test = max(m1["lr_test"], m1["xgb_test"])

    if best_old_test > 0:
        print(f"  Modelo 1 (ganador) - Antes:   {best_old_test:.4f}")
        print(f"  Modelo 1 (ganador) - Despues:  {best_new_test:.4f}")
        diff = best_new_test - best_old_test
        print(f"  Diferencia:                    {diff:+.4f} ({diff*100:+.2f}%)")
    else:
        print(f"  Modelo 1 (ganador): Test={best_new_test:.4f}")

    print(f"  Modelo 2 (metodo):  Test={results['model2']['test']:.4f}")
    print(f"  Modelo 3 (finish):  Test={results['model3']['test']:.4f}")
    print(f"  Modelo 4 (round):   Test={results['model4']['test']:.4f}")
    print(f"\n  Total features: {len(feature_cols)} (antes: ~134)")
    print("=" * 60)


if __name__ == "__main__":
    main()