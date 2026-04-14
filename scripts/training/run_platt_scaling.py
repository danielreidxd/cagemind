from __future__ import annotations

import json
import pickle
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")  # Sin GUI
import matplotlib.pyplot as plt
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier
    HAS_XGB = False
    print("XGBoost no disponible, usando GradientBoosting")

# ============================================================
# RUTAS
# ============================================================

PROJECT_ROOT = Path(__file__).parent
DB_PATH = PROJECT_ROOT / "db" / "ufc_predictor.db"
DATASET_V2 = PROJECT_ROOT / "data" / "processed" / "training_dataset_v2.csv"
DATASET_V1 = PROJECT_ROOT / "data" / "processed" / "training_dataset.csv"
MODELS_PATH = PROJECT_ROOT / "ml" / "models" / "ufc_predictor_models.pkl"
FEATURES_PATH = PROJECT_ROOT / "ml" / "models" / "feature_names.json"
OUTPUT_DIR = PROJECT_ROOT / "ml" / "calibration"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROB_CAP = 0.85  # Safety net: ninguna probabilidad > 85%


def load_dataset():
    """Carga el mejor dataset disponible."""
    if DATASET_V2.exists():
        print(f"Usando dataset v2 (con Sherdog): {DATASET_V2}")
        return pd.read_csv(DATASET_V2)
    elif DATASET_V1.exists():
        print(f"Usando dataset v1: {DATASET_V1}")
        return pd.read_csv(DATASET_V1)
    else:
        print("ERROR: No se encontró training dataset.")
        print("Ejecuta primero:")
        print("  python run_phase3_features.py")
        print("  python retrain_with_sherdog.py  (opcional)")
        raise FileNotFoundError("No training dataset found")


def get_feature_columns(df):
    """Obtener columnas de features (excluyendo targets y metadata)."""
    exclude = {
        "fighter_a", "fighter_b", "fight_id", "event_id", "date",
        "target_winner", "target_method", "target_round",
        "target_goes_distance", "weight_class",
    }
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    return [c for c in numeric_cols if c not in exclude]


def prepare_data(df, feature_cols):
    """Prepara X, y para el modelo winner."""
    X = df[feature_cols].copy()

    # Eliminar columnas 100% nulas
    all_null = X.columns[X.isnull().all()].tolist()
    if all_null:
        print(f"  Eliminando {len(all_null)} columnas 100% nulas")
        X = X.drop(columns=all_null)
        feature_cols = [c for c in feature_cols if c not in all_null]

    # Imputar NaN con medianas
    imputer = SimpleImputer(strategy="median")
    X_imputed = pd.DataFrame(
        imputer.fit_transform(X), columns=feature_cols, index=X.index
    )

    y = df["target_winner"]
    mask = y.notna()
    X_clean = X_imputed[mask]
    y_clean = y[mask].astype(int)

    return X_clean, y_clean, feature_cols, imputer


def plot_reliability_diagram(y_true, prob_uncal, prob_cal, output_path):
    """Genera reliability diagram comparando antes vs después de calibrar."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for ax, probs, title, color in [
        (axes[0], prob_uncal, "Sin calibrar (raw)", "#C8102E"),
        (axes[1], prob_cal, "Con Platt Scaling", "#22C55E"),
    ]:
        fraction_pos, mean_predicted = calibration_curve(
            y_true, probs, n_bins=10, strategy="uniform"
        )
        ax.plot([0, 1], [0, 1], "k--", label="Perfectamente calibrado", alpha=0.5)
        ax.plot(mean_predicted, fraction_pos, "o-", color=color, label="Modelo", linewidth=2)
        ax.set_xlabel("Probabilidad predicha", fontsize=12)
        ax.set_ylabel("Fracción real de positivos", fontsize=12)
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.legend(loc="lower right")
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.grid(True, alpha=0.3)

        brier = brier_score_loss(y_true, probs)
        ax.text(0.05, 0.92, f"Brier Score: {brier:.4f}",
                transform=ax.transAxes, fontsize=11,
                bbox=dict(boxstyle="round", facecolor="white", alpha=0.8))

    plt.suptitle("CageMind — Calibración de Probabilidades", fontsize=16, fontweight="bold")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Reliability diagram: {output_path}")


def apply_cap(prob_a, prob_b, cap=PROB_CAP):
    """Aplica cap de seguridad y re-normaliza."""
    ca = min(prob_a, cap)
    cb = min(prob_b, cap)
    total = ca + cb
    return ca / total, cb / total


def main():
    print("=" * 60)
    print("CAGEMIND — PLATT SCALING (CALIBRACIÓN)")
    print("=" * 60)

    # 1. Cargar datos
    df = load_dataset()
    feature_cols = get_feature_columns(df)
    X, y, feature_cols, imputer = prepare_data(df, feature_cols)
    print(f"Dataset: {len(X)} peleas, {len(feature_cols)} features")

    # 2. Split: train (70%) / calibration (15%) / test (15%)
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )
    X_train, X_cal, y_train, y_cal = train_test_split(
        X_trainval, y_trainval, test_size=0.176,  # 0.176 de 0.85 ≈ 0.15 del total
        random_state=42, stratify=y_trainval
    )
    print(f"Split: train={len(X_train)}, calibration={len(X_cal)}, test={len(X_test)}")

    # 3. Entrenar modelo base (sin calibrar)
    print("\n--- Modelo SIN calibrar ---")
    if HAS_XGB:
        base_model = XGBClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1,
            random_state=42, eval_metric="logloss", verbosity=0
        )
    else:
        base_model = GradientBoostingClassifier(
            n_estimators=200, max_depth=5, learning_rate=0.1, random_state=42
        )

    # También entrenar LogReg para comparar (con scaler para convergencia)
    lr_model = Pipeline([
        ("scaler", StandardScaler()),
        ("lr", LogisticRegression(max_iter=2000, random_state=42, C=0.5))
    ])

    base_model.fit(X_train, y_train)
    lr_model.fit(X_train, y_train)

    # Probabilidades raw en test
    prob_base = base_model.predict_proba(X_test)[:, 1]
    prob_lr = lr_model.predict_proba(X_test)[:, 1]

    acc_base = accuracy_score(y_test, (prob_base >= 0.5).astype(int))
    acc_lr = accuracy_score(y_test, (prob_lr >= 0.5).astype(int))
    brier_base = brier_score_loss(y_test, prob_base)
    brier_lr = brier_score_loss(y_test, prob_lr)

    print(f"  XGBoost:  Accuracy={acc_base:.4f}, Brier={brier_base:.4f}")
    print(f"  LogReg:   Accuracy={acc_lr:.4f}, Brier={brier_lr:.4f}")

    # Elegir mejor modelo base
    if acc_base >= acc_lr:
        best_base = base_model
        best_name = "XGBoost"
        prob_uncal = prob_base
    else:
        best_base = lr_model
        best_name = "LogReg"
        prob_uncal = prob_lr
    print(f"  Mejor modelo base: {best_name}")

    # 4. Calibrar con Platt Scaling
    print("\n--- Calibración con Platt Scaling ---")

    # Re-entrenar con calibración integrada (cv=5 hace fit+calibrate)
    from sklearn.base import clone
    cal_base = clone(best_base)
    calibrated_model = CalibratedClassifierCV(
        cal_base, method="sigmoid", cv=5
    )
    X_traincal = pd.concat([X_train, X_cal])
    y_traincal = pd.concat([y_train, y_cal])
    calibrated_model.fit(X_traincal, y_traincal)

    # Probabilidades calibradas en test
    prob_cal = calibrated_model.predict_proba(X_test)[:, 1]
    acc_cal = accuracy_score(y_test, (prob_cal >= 0.5).astype(int))
    brier_cal = brier_score_loss(y_test, prob_cal)

    print(f"  Calibrado: Accuracy={acc_cal:.4f}, Brier={brier_cal:.4f}")
    print(f"  Mejora Brier: {brier_base - brier_cal:+.4f} (menor = mejor)")

    # 5. Comparar con la calibración lineal actual
    print("\n--- Comparación con calibración lineal actual ---")
    COMPRESSION = 0.75
    prob_linear = 0.5 + (prob_uncal - 0.5) * COMPRESSION
    prob_linear = np.clip(prob_linear, 1 - PROB_CAP, PROB_CAP)
    brier_linear = brier_score_loss(y_test, prob_linear)
    print(f"  Calibración lineal (actual):  Brier={brier_linear:.4f}")
    print(f"  Platt Scaling (nuevo):        Brier={brier_cal:.4f}")
    print(f"  Diferencia:                   {brier_linear - brier_cal:+.4f}")

    # 6. Reliability diagrams
    print("\n--- Generando gráficas ---")
    plot_reliability_diagram(
        y_test, prob_uncal, prob_cal,
        OUTPUT_DIR / "reliability_diagram.png"
    )

    # 7. Tabla de conversión
    print("\n--- Tabla de conversión ---")
    print(f"{'Raw modelo':>12} | {'Lineal (actual)':>16} | {'Platt (nuevo)':>14}")
    print("-" * 48)
    for raw_prob in [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55, 0.50]:
        # Lineal actual
        lin = 0.5 + (raw_prob - 0.5) * COMPRESSION
        lin = min(lin, PROB_CAP)
        lin_b = 1 - lin
        total = lin + lin_b
        lin = lin / total

        idx = np.argmin(np.abs(prob_uncal - raw_prob))
        platt = prob_cal[idx]

        platt_capped = min(platt, PROB_CAP)
        platt_capped_b = max(1 - platt_capped, 1 - PROB_CAP)
        total_p = platt_capped + platt_capped_b
        platt_final = platt_capped / total_p

        print(f"  {raw_prob*100:5.1f}% vs {(1-raw_prob)*100:4.1f}% | "
              f"{lin*100:5.1f}% vs {(1-lin)*100:4.1f}% | "
              f"{platt_final*100:5.1f}% vs {(1-platt_final)*100:4.1f}%")

    # 8. Entrenar modelo final (todo el dataset excepto test)
    print("\n--- Entrenando modelo final con Platt Scaling ---")

    final_base = clone(best_base)
    final_calibrated = CalibratedClassifierCV(
        final_base, method="sigmoid", cv=5
    )
    final_calibrated.fit(X_traincal, y_traincal)

    # Validar en test
    final_prob = final_calibrated.predict_proba(X_test)[:, 1]
    final_acc = accuracy_score(y_test, (final_prob >= 0.5).astype(int))
    final_brier = brier_score_loss(y_test, final_prob)
    print(f"  Final: Accuracy={final_acc:.4f}, Brier={final_brier:.4f}")

    # 9. Guardar modelo calibrado
    # Cargar bundle existente y reemplazar el modelo winner
    if MODELS_PATH.exists():
        with open(MODELS_PATH, "rb") as f:
            bundle = pickle.load(f)

        # Backup
        backup = MODELS_PATH.with_suffix(".pkl.pre_platt")
        import shutil
        shutil.copy2(MODELS_PATH, backup)
        print(f"  Backup modelo anterior: {backup}")

        # Reemplazar winner model
        bundle["winner_model"] = final_calibrated
        bundle["winner_model_calibrated"] = True
        bundle["imputer"] = imputer

        with open(MODELS_PATH, "wb") as f:
            pickle.dump(bundle, f)
        print(f"  Modelo calibrado guardado: {MODELS_PATH}")

        # Guardar features
        with open(FEATURES_PATH, "w") as f:
            json.dump(feature_cols, f)
    else:
        print(f"  ADVERTENCIA: No se encontró {MODELS_PATH}")
        print("  Guardando modelo calibrado por separado...")
        cal_path = OUTPUT_DIR / "calibrated_winner_model.pkl"
        with open(cal_path, "wb") as f:
            pickle.dump({
                "winner_model": final_calibrated,
                "feature_names": feature_cols,
                "imputer": imputer,
            }, f)
        print(f"  Guardado en: {cal_path}")

    # 10. Guardar resultados
    results = {
        "base_model": best_name,
        "accuracy_uncalibrated": float(acc_base if best_name == "XGBoost" else acc_lr),
        "accuracy_calibrated": float(final_acc),
        "brier_uncalibrated": float(brier_base if best_name == "XGBoost" else brier_lr),
        "brier_calibrated": float(final_brier),
        "brier_linear_old": float(brier_linear),
        "brier_improvement_vs_linear": float(brier_linear - final_brier),
        "prob_cap": PROB_CAP,
        "train_size": len(X_traincal),
        "test_size": len(X_test),
        "features": len(feature_cols),
    }
    results_path = OUTPUT_DIR / "calibration_results.json"
    with open(results_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Resultados: {results_path}")

    # Resumen final
    print()
    print("=" * 60)
    print("RESUMEN PLATT SCALING")
    print("=" * 60)
    print(f"  Modelo base:      {best_name}")
    print(f"  Accuracy:         {final_acc:.4f} (sin cambio significativo)")
    print(f"  Brier Score:")
    print(f"    Sin calibrar:   {brier_base if best_name == 'XGBoost' else brier_lr:.4f}")
    print(f"    Lineal (viejo): {brier_linear:.4f}")
    print(f"    Platt (nuevo):  {final_brier:.4f}")
    print(f"  Cap de seguridad: {PROB_CAP*100:.0f}%")
    print()
    print("SIGUIENTE PASO:")
    print("  Actualizar backend/app.py:")
    print("  1. ELIMINAR la función calibrate_proba() actual")
    print("  2. El modelo calibrado ya produce probabilidades realistas")
    print("  3. Solo mantener el cap de 85% como safety net")
    print()
    print("  En la función predict_fight(), cambiar:")
    print("    raw_proba = model.predict_proba(X)[0]")
    print("    prob_a = min(raw_proba[1], 0.85)")
    print("    prob_b = 1 - prob_a")
    print("    # Re-normalizar si ambos tocaron cap")
    print("    total = prob_a + prob_b")
    print("    prob_a, prob_b = prob_a/total, prob_b/total")
    print("=" * 60)


if __name__ == "__main__":
    main()
