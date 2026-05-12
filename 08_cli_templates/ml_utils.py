#!/usr/bin/env python3
"""
ml_utils.py

A production-ready ML toolkit for training, evaluating, and managing models.
Designed for offline developer toolkits.

Features:
* Smart data splitting (handles stratification automatically)
* Safe scaling (auto-selects numeric columns, handles sparse data)
* Dynamic model loading (supports any sklearn-compatible model)
* Automatic Pipelining (optional: bundles scaler + model to prevent inference errors)
* Feature Importance extraction

CLI Examples:
    python ml_utils.py split data.csv target --out-dir ./splits
    python ml_utils.py train train.csv --target label --model xgboost.XGBClassifier
    python ml_utils.py evaluate model.pkl test.csv --target label --classification
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import (
    MinMaxScaler,
    RobustScaler,
    StandardScaler,
    OneHotEncoder,
)

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ----------------------------------------------------------------------
# 1️⃣  Dataset Split
# ----------------------------------------------------------------------
def split_dataset(
    df: pd.DataFrame,
    target_column: str,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = False,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """
    Split DataFrame into train/test with optional stratification.
    Automatically detects if stratification is possible for classification.
    """
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in DataFrame")

    X = df.drop(columns=[target_column])
    y = df[target_column]

    strat_arg = None
    if stratify:
        # Check if target is suitable for stratification
        if y.dtype.kind in 'biuf': # Numeric types
             # If numeric but few unique values, treat as classification
            if y.nunique() / len(y) < 0.1: 
                strat_arg = y
                log.info("Using stratification (detected discrete target)")
        else:
            strat_arg = y
            log.info("Using stratification (categorical target)")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=strat_arg
    )
    
    log.info(f"Split complete. Train: {len(X_train)} rows, Test: {len(X_test)} rows")
    return X_train, X_test, y_train, y_test

# ----------------------------------------------------------------------
# 2️⃣  Feature Scaling (Smart)
# ----------------------------------------------------------------------
def scale_features(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    method: str = "standard",
    columns: Optional[List[str]] = None,
    save_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, Any]:
    """
    Scale numeric features. Auto-detects numeric columns if 'columns' is None.
    Returns the scaled DataFrames AND the fitted scaler object.
    """
    # Auto-select numeric columns if not provided
    if columns is None:
        columns = train_df.select_dtypes(include=['number']).columns.tolist()
        log.info(f"Auto-detected {len(columns)} numeric columns for scaling.")
    
    if not columns:
        log.warning("No numeric columns found. Skipping scaling.")
        return train_df, test_df, None

    scaler_map = {
        "standard": StandardScaler(),
        "minmax": MinMaxScaler(),
        "robust": RobustScaler(),
    }
    if method not in scaler_map:
        raise ValueError(f"Unsupported method: {method}")

    scaler = scaler_map[method]
    
    # Fit on train, transform both
    train_df = train_df.copy()
    test_df = test_df.copy()
    
    train_df[columns] = scaler.fit_transform(train_df[columns])
    test_df[columns] = scaler.transform(test_df[columns])

    if save_path:
        joblib.dump(scaler, save_path)
        log.info(f"Saved {method} scaler to {save_path}")

    return train_df, test_df, scaler


# ----------------------------------------------------------------------
# 3️⃣  Model Training (Dynamic Import + Pipeline Support)
# ----------------------------------------------------------------------
def get_model(model_type: str, params: Optional[Dict] = None) -> BaseEstimator:
    """
    Dynamically import and instantiate a model.
    Supports shorthand aliases (e.g. 'random_forest') or full import paths.
    """
    # Registry of convenient aliases
    ALIASES = {
        "logistic_regression": "sklearn.linear_model.LogisticRegression",
        "random_forest": "sklearn.ensemble.RandomForestClassifier",
        "gradient_boosting": "sklearn.ensemble.GradientBoostingClassifier",
        "svm": "sklearn.svm.SVC",
        "linear_regression": "sklearn.linear_model.LinearRegression",
        "ridge": "sklearn.linear_model.Ridge",
        "lasso": "sklearn.linear_model.Lasso",
    }

    class_path = ALIASES.get(model_type, model_type)
    
    try:
        if "." in class_path:
            module_name, class_name = class_path.rsplit(".", 1)
            module = importlib.import_module(module_name)
            ModelClass = getattr(module, class_name)
        else:
            raise ValueError(f"Invalid model identifier: {model_type}")
        
        model = ModelClass(**(params or {}))
        log.info(f"Initialized model: {class_name}")
        return model
    except ImportError as e:
        log.error(f"Could not import model: {class_path}. Error: {e}")
        raise

def train_model(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    model_type: str,
    params: Optional[Dict[str, Any]] = None,
    scaler: Optional[Any] = None,  # Accept a fitted scaler to create a pipeline
    random_state: int = 42,
) -> BaseEstimator:
    """
    Train a model. If 'scaler' is provided, returns a Pipeline.
    This is best practice to ensure scaling is applied during inference.
    """
    model = get_model(model_type, params)
    
    # Inject random_state if supported
    if hasattr(model, 'random_state') and 'random_state' not in (params or {}):
        model.set_params(random_state=random_state)

    if scaler:
        log.info("Bundling scaler with model into a Pipeline.")
        pipeline = Pipeline([
            ('scaler', scaler),
            ('model', model)
        ])
        pipeline.fit(X_train, y_train)
        return pipeline
    else:
        model.fit(X_train, y_train)
        return model

def save_model(model: BaseEstimator, path: Union[str, Path]) -> None:
    joblib.dump(model, path)
    log.info(f"Model saved to {path}")

def load_model(path: Union[str, Path]) -> BaseEstimator:
    return joblib.load(path)


# ----------------------------------------------------------------------
# 4️⃣  Evaluation
# ----------------------------------------------------------------------
def evaluate_model(
    model: BaseEstimator,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    problem_type: str = "auto",  # 'auto', 'classification', 'regression'
) -> Dict[str, float]:
    """
    Evaluate model metrics. Auto-detects problem type if set to 'auto'.
    """
    y_pred = model.predict(X_test)
    
    # Determine problem type
    if problem_type == "auto":
        # Heuristic: if target has few unique values or is non-numeric, treat as classification
        is_classification = y_test.dtype.kind not in 'biuf' or y_test.nunique() < 20
        problem_type = "classification" if is_classification else "regression"
        log.info(f"Auto-detected problem type: {problem_type}")

    results = {}
    
    if problem_type == "classification":
        results["accuracy"] = accuracy_score(y_test, y_pred)
        # Handle binary/multiclass averaging for F1/Precision/Recall
        avg_method = "binary" if y_test.nunique() == 2 else "weighted"
        
        results["f1"] = f1_score(y_test, y_pred, average=avg_method, zero_division=0)
        results["precision"] = precision_score(y_test, y_pred, average=avg_method, zero_division=0)
        results["recall"] = recall_score(y_test, y_pred, average=avg_method, zero_division=0)
        
        # ROC AUC (requires predict_proba)
        if hasattr(model, "predict_proba"):
            try:
                prob = model.predict_proba(X_test)
                # Binary case
                if prob.shape[1] == 2:
                    results["roc_auc"] = roc_auc_score(y_test, prob[:, 1])
                else:
                    results["roc_auc"] = roc_auc_score(y_test, prob, multi_class='ovr')
            except Exception as e:
                log.warning(f"Could not calculate ROC AUC: {e}")

    else: # Regression
        results["r2"] = r2_score(y_test, y_pred)
        results["mse"] = mean_squared_error(y_test, y_pred)
        results["mae"] = mean_absolute_error(y_test, y_pred)

    # Pretty print
    print("\n--- Evaluation Report ---")
    for k, v in results.items():
        print(f"{k.upper():<10}: {v:.4f}")
    print("-------------------------")
    
    return results


# ----------------------------------------------------------------------
# 5️⃣  Feature Importance
# ----------------------------------------------------------------------
def get_feature_importance(model: BaseEstimator, feature_names: List[str]) -> pd.DataFrame:
    """
    Extract feature importance from a trained model or Pipeline.
    Supports Tree-based models and Linear models.
    """
    # If pipeline, extract the final estimator
    if isinstance(model, Pipeline):
        estimator = model.named_steps['model']
        # Note: Feature names might have changed if pipeline has preprocessing
        # For simplicity, we assume the pipeline steps don't change feature order 
        # (which is true for Scaler but not for OneHotEncoder)
    else:
        estimator = model

    if hasattr(estimator, 'feature_importances_'):
        importances = estimator.feature_importances_
    elif hasattr(estimator, 'coef_'):
        importances = abs(estimator.coef_).flatten() # Absolute value for importance
    else:
        log.warning("Model does not have feature_importances_ or coef_ attributes.")
        return pd.DataFrame()

    df = pd.DataFrame({
        'feature': feature_names,
        'importance': importances
    }).sort_values('importance', ascending=False)
    
    return df


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ML Toolkit CLI", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Split
    p_split = sub.add_parser("split", help="Split dataset")
    p_split.add_argument("csv", type=Path, help="Input CSV")
    p_split.add_argument("target", help="Target column")
    p_split.add_argument("--out-dir", type=Path, default=Path("."), help="Output directory")
    p_split.add_argument("--test-size", type=float, default=0.2)
    p_split.add_argument("--stratify", action="store_true")

    # Train
    p_train = sub.add_parser("train", help="Train model")
    p_train.add_argument("train_csv", type=Path)
    p_train.add_argument("--target", required=True)
    p_train.add_argument("--model", default="random_forest", help="Model alias or import path (e.g. sklearn.ensemble.RandomForestClassifier)")
    p_train.add_argument("--params", help="JSON dict of model params")
    p_train.add_argument("--scaler", type=Path, help="Path to saved scaler (will create a Pipeline)")
    p_train.add_argument("--out", type=Path, default=Path("model.pkl"), help="Output model path")

    # Evaluate
    p_eval = sub.add_parser("evaluate", help="Evaluate model")
    p_eval.add_argument("model_path", type=Path)
    p_eval.add_argument("test_csv", type=Path)
    p_eval.add_argument("--target", required=True)
    p_eval.add_argument("--type", choices=["auto", "classification", "regression"], default="auto")

    # Importance
    p_imp = sub.add_parser("importance", help="Get feature importance")
    p_imp.add_argument("model_path", type=Path)
    p_imp.add_argument("train_csv", type=Path, help="CSV used for training (to get column names)")
    p_imp.add_argument("--target", required=True)
    p_imp.add_argument("--out", type=Path, default=None, help="Save importance CSV")

    return parser

def _dispatch(args):
    if args.cmd == "split":
        df = pd.read_csv(args.csv)
        X_train, X_test, y_train, y_test = split_dataset(df, args.target, stratify=args.stratify)
        # Concat back to CSV
        train_df = pd.concat([X_train, y_train], axis=1)
        test_df = pd.concat([X_test, y_test], axis=1)
        train_df.to_csv(args.out_dir / "train.csv", index=False)
        test_df.to_csv(args.out_dir / "test.csv", index=False)
        log.info("Saved train.csv and test.csv")

    elif args.cmd == "train":
        df = pd.read_csv(args.train_csv)
        y = df[args.target]
        X = df.drop(columns=[args.target])
        
        params = json.loads(args.params) if args.params else None
        scaler = load_model(args.scaler) if args.scaler else None
        
        model = train_model(X, y, args.model, params=params, scaler=scaler)
        save_model(model, args.out)

    elif args.cmd == "evaluate":
        model = load_model(args.model_path)
        df = pd.read_csv(args.test_csv)
        y = df[args.target]
        X = df.drop(columns=[args.target])
        evaluate_model(model, X, y, problem_type=args.type)

    elif args.cmd == "importance":
        model = load_model(args.model_path)
        df = pd.read_csv(args.train_csv)
        features = df.drop(columns=[args.target]).columns.tolist()
        
        imp_df = get_feature_importance(model, features)
        print(imp_df.head(20))
        if args.out:
            imp_df.to_csv(args.out, index=False)

def main():
    parser = _build_cli()
    args = parser.parse_args()
    try:
        _dispatch(args)
    except Exception as e:
        log.exception("Error during execution")
        sys.exit(1)

if __name__ == "__main__":
    main()
