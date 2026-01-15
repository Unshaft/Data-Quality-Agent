"""
Script de génération de datasets de test pour le Data Quality Agent.

Génère des datasets avec des problèmes de qualité intentionnels :
- Valeurs manquantes (différents seuils)
- Outliers extrêmes
- Valeurs négatives impossibles
- Dataset vide

Usage:
    python scripts/generate_test_data.py
"""

import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Répertoire de sortie
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "test"


def generate_clean_dataset(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset propre de base.

    Args:
        n_rows: Nombre de lignes à générer.

    Returns:
        DataFrame propre sans problèmes de qualité.
    """
    np.random.seed(42)

    data = {
        "user_id": range(1, n_rows + 1),
        "age": np.random.randint(18, 80, n_rows),
        "gender": np.random.choice(["Male", "Female", "Other"], n_rows),
        "country": np.random.choice(["France", "USA", "UK", "Germany", "Spain"], n_rows),
        "income_level": np.random.choice(["Low", "Medium", "High"], n_rows),
        "weekly_purchases": np.random.randint(0, 20, n_rows),
        "monthly_spend": np.random.uniform(50, 500, n_rows).round(2),
        "average_order_value": np.random.uniform(20, 150, n_rows).round(2),
        "cart_abandonment_rate": np.random.uniform(0, 1, n_rows).round(3),
        "loyalty_program_member": np.random.choice(["Yes", "No"], n_rows),
        "account_age_months": np.random.randint(1, 120, n_rows),
        "last_purchase_date": pd.date_range(end="2024-12-31", periods=n_rows).strftime("%Y-%m-%d"),
    }

    return pd.DataFrame(data)


def generate_missing_values_warning(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset avec 25% de valeurs manquantes (WARNING).
    """
    df = generate_clean_dataset(n_rows)

    # Injecter 25% de valeurs manquantes dans 'age'
    missing_idx = np.random.choice(df.index, size=int(n_rows * 0.25), replace=False)
    df.loc[missing_idx, "age"] = np.nan

    # Injecter 30% dans 'monthly_spend'
    missing_idx = np.random.choice(df.index, size=int(n_rows * 0.30), replace=False)
    df.loc[missing_idx, "monthly_spend"] = np.nan

    logger.info(f"Dataset généré: 25% missing dans 'age', 30% dans 'monthly_spend'")
    return df


def generate_missing_values_reject(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset avec >40% de valeurs manquantes (REJECT).
    """
    df = generate_clean_dataset(n_rows)

    # Injecter 45% de valeurs manquantes dans 'age' (colonne critique)
    missing_idx = np.random.choice(df.index, size=int(n_rows * 0.45), replace=False)
    df.loc[missing_idx, "age"] = np.nan

    # Injecter 50% dans 'user_id' (colonne critique)
    missing_idx = np.random.choice(df.index, size=int(n_rows * 0.50), replace=False)
    df.loc[missing_idx, "user_id"] = np.nan

    logger.info(f"Dataset généré: 45% missing dans 'age', 50% dans 'user_id'")
    return df


def generate_outliers_dataset(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset avec >5% d'outliers extrêmes (WARNING).
    """
    df = generate_clean_dataset(n_rows)

    # Injecter 10% d'outliers extrêmes dans 'monthly_spend'
    outlier_idx = np.random.choice(df.index, size=int(n_rows * 0.10), replace=False)
    df.loc[outlier_idx, "monthly_spend"] = np.random.uniform(5000, 50000, len(outlier_idx))

    # Injecter 8% d'outliers dans 'average_order_value'
    outlier_idx = np.random.choice(df.index, size=int(n_rows * 0.08), replace=False)
    df.loc[outlier_idx, "average_order_value"] = np.random.uniform(2000, 10000, len(outlier_idx))

    logger.info(f"Dataset généré: 10% outliers dans 'monthly_spend', 8% dans 'average_order_value'")
    return df


def generate_negative_values_dataset(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset avec des valeurs négatives impossibles (WARNING).
    """
    df = generate_clean_dataset(n_rows)

    # Injecter des âges négatifs (impossible)
    negative_idx = np.random.choice(df.index, size=int(n_rows * 0.05), replace=False)
    df.loc[negative_idx, "age"] = np.random.randint(-50, -1, len(negative_idx))

    # Injecter des dépenses mensuelles négatives
    negative_idx = np.random.choice(df.index, size=int(n_rows * 0.03), replace=False)
    df.loc[negative_idx, "monthly_spend"] = np.random.uniform(-500, -10, len(negative_idx))

    # Injecter des account_age_months négatifs
    negative_idx = np.random.choice(df.index, size=int(n_rows * 0.02), replace=False)
    df.loc[negative_idx, "account_age_months"] = np.random.randint(-24, -1, len(negative_idx))

    logger.info(f"Dataset généré: valeurs négatives dans 'age', 'monthly_spend', 'account_age_months'")
    return df


def generate_empty_dataset() -> pd.DataFrame:
    """
    Génère un dataset vide (REJECT - DQ-02).
    """
    columns = [
        "user_id", "age", "gender", "country", "income_level",
        "weekly_purchases", "monthly_spend", "average_order_value",
        "cart_abandonment_rate", "loyalty_program_member",
        "account_age_months", "last_purchase_date"
    ]
    logger.info("Dataset généré: 0 lignes (vide)")
    return pd.DataFrame(columns=columns)


def generate_multiple_issues_dataset(n_rows: int = 1000) -> pd.DataFrame:
    """
    Génère un dataset avec plusieurs types de problèmes combinés.
    """
    df = generate_clean_dataset(n_rows)

    # 22% valeurs manquantes dans 'age'
    missing_idx = np.random.choice(df.index, size=int(n_rows * 0.22), replace=False)
    df.loc[missing_idx, "age"] = np.nan

    # 7% outliers dans 'monthly_spend'
    outlier_idx = np.random.choice(df.index, size=int(n_rows * 0.07), replace=False)
    df.loc[outlier_idx, "monthly_spend"] = np.random.uniform(3000, 20000, len(outlier_idx))

    # 4% valeurs négatives dans 'weekly_purchases'
    negative_idx = np.random.choice(df.index, size=int(n_rows * 0.04), replace=False)
    df.loc[negative_idx, "weekly_purchases"] = np.random.randint(-10, -1, len(negative_idx))

    logger.info("Dataset généré: 22% missing + 7% outliers + 4% négatifs")
    return df


def main() -> int:
    """
    Génère tous les datasets de test.
    """
    logger.info("=" * 60)
    logger.info("Génération des datasets de test")
    logger.info("=" * 60)

    # Créer le répertoire de sortie
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logger.info(f"Répertoire de sortie: {OUTPUT_DIR}")

    # Datasets à générer
    datasets = [
        ("clean.csv", generate_clean_dataset, "Dataset propre (ACCEPT attendu)"),
        ("missing_warning.csv", generate_missing_values_warning, "25-30% missing (WARNING attendu)"),
        ("missing_reject.csv", generate_missing_values_reject, "45-50% missing (REJECT attendu)"),
        ("outliers.csv", generate_outliers_dataset, "8-10% outliers (WARNING attendu)"),
        ("negative_values.csv", generate_negative_values_dataset, "Valeurs négatives (WARNING attendu)"),
        ("empty.csv", generate_empty_dataset, "Dataset vide (REJECT attendu)"),
        ("multiple_issues.csv", generate_multiple_issues_dataset, "Problèmes multiples (WARNING attendu)"),
    ]

    logger.info("-" * 60)

    for filename, generator_func, description in datasets:
        filepath = OUTPUT_DIR / filename
        df = generator_func()
        df.to_csv(filepath, index=False)
        logger.info(f"[OK] {filename:25} | {len(df):5} lignes | {description}")

    logger.info("-" * 60)
    logger.info(f"Tous les datasets ont été générés dans: {OUTPUT_DIR}")
    logger.info("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
