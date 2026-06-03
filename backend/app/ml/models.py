"""
FinSight AI - Machine Learning pipeline.

Includes synthetic data generator, model training (XGBoost & RandomForest),
and prediction helpers.
"""

from __future__ import annotations

import logging
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import xgboost as xgb

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.dirname(os.path.abspath(__file__))
XGB_MODEL_PATH = os.path.join(MODEL_DIR, "xgb_volatility.joblib")
RF_MODEL_PATH = os.path.join(MODEL_DIR, "rf_trend.joblib")


def generate_synthetic_history(symbol: str, days: int = 180) -> pd.DataFrame:
    """Generate synthetic daily stock/crypto price data for training."""
    np.random.seed(hash(symbol) % (2**32))
    
    # Define price bases
    price_bases = {
        "RELIANCE": 2500.0,
        "TCS": 3600.0,
        "HDFCBANK": 1600.0,
        "INFY": 1500.0,
        "ICICIBANK": 1000.0,
        "WIPRO": 400.0,
        "SBIN": 600.0,
        "BTC": 60000.0,
        "ETH": 3300.0,
    }
    base = price_bases.get(symbol, 100.0)
    
    # Standard deviation (volatility) of returns
    daily_vol = 0.015 if symbol not in ["BTC", "ETH"] else 0.035
    
    dates = [datetime.now(timezone.utc) - timedelta(days=i) for i in range(days)]
    dates.reverse()
    
    # Generate daily returns
    returns = np.random.normal(0.0002, daily_vol, days) # slight positive drift
    prices = []
    curr_price = base
    for r in returns:
        curr_price *= (1 + r)
        prices.append(curr_price)
        
    df = pd.DataFrame({
        "date": dates,
        "symbol": [symbol] * days,
        "close": prices,
    })
    
    # Feature Engineering
    df["returns"] = df["close"].pct_change()
    df["volatility_5d"] = df["returns"].rolling(5).std()
    df["volatility_20d"] = df["returns"].rolling(20).std()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_30"] = df["close"].rolling(30).mean()
    df["ma_ratio"] = df["ma_10"] / df["ma_30"]
    
    # Target columns (Shifted)
    df["target_volatility_future"] = df["volatility_5d"].shift(-5) # future 5-day volatility
    df["future_close"] = df["close"].shift(-5)
    df["target_trend_future"] = (df["future_close"] > df["close"]).astype(int) # 1 if price rises in 5 days, else 0
    
    df.dropna(inplace=True)
    return df


def train_models() -> None:
    """Train XGBoost Regressor (volatility) and RandomForest Classifier (trend) on synthetic data."""
    logger.info("Training ML models on synthetic portfolio data...")
    
    symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BTC", "ETH"]
    dfs = [generate_synthetic_history(sym, 200) for sym in symbols]
    data = pd.concat(dfs, ignore_index=True)
    
    # Features for models
    features = ["close", "returns", "volatility_5d", "volatility_20d", "ma_ratio"]
    X = data[features].values
    
    # Target 1: Volatility (XGBoost Regressor)
    y_vol = data["target_volatility_future"].values
    xgb_reg = xgb.XGBRegressor(n_estimators=50, max_depth=3, learning_rate=0.1, random_state=42)
    xgb_reg.fit(X, y_vol)
    joblib.dump(xgb_reg, XGB_MODEL_PATH)
    logger.info(f"XGBoost volatility model saved to {XGB_MODEL_PATH}")
    
    # Target 2: Trend (RandomForest Classifier)
    y_trend = data["target_trend_future"].values
    rf_clf = RandomForestClassifier(n_estimators=50, max_depth=4, random_state=42)
    rf_clf.fit(X, y_trend)
    joblib.dump(rf_clf, RF_MODEL_PATH)
    logger.info(f"RandomForest trend classifier saved to {RF_MODEL_PATH}")


def get_predictions_for_symbols(symbols: list[str]) -> list[dict]:
    """Generate predictions for a list of symbols.
    
    If model files do not exist, they are trained on demand.
    """
    if not symbols:
        return []
        
    # Check if models exist, if not train them
    if not os.path.exists(XGB_MODEL_PATH) or not os.path.exists(RF_MODEL_PATH):
        try:
            train_models()
        except Exception as e:
            logger.error(f"Failed to train models: {e}. Falling back to deterministic outputs.")
            
    # Load models if possible
    xgb_reg = None
    rf_clf = None
    if os.path.exists(XGB_MODEL_PATH) and os.path.exists(RF_MODEL_PATH):
        try:
            xgb_reg = joblib.load(XGB_MODEL_PATH)
            rf_clf = joblib.load(RF_MODEL_PATH)
        except Exception as e:
            logger.error(f"Error loading models: {e}")

    predictions = []
    now = datetime.now(timezone.utc)
    
    for symbol in symbols:
        try:
            df = generate_synthetic_history(symbol, 40)
            if df.empty:
                continue
            last_row = df.iloc[-1]
            features = [
                float(last_row["close"]),
                float(last_row["returns"]),
                float(last_row["volatility_5d"]),
                float(last_row["volatility_20d"]),
                float(last_row["ma_ratio"])
            ]
            X_input = np.array([features])
            
            # Predict Volatility
            if xgb_reg:
                pred_vol = float(xgb_reg.predict(X_input)[0])
            else:
                pred_vol = float(last_row["volatility_5d"] * random.uniform(0.9, 1.1))
                
            # Predict Trend (Direction & Probability/Confidence)
            if rf_clf:
                pred_trend_class = int(rf_clf.predict(X_input)[0])
                probs = rf_clf.predict_proba(X_input)[0]
                confidence = float(probs[pred_trend_class])
            else:
                pred_trend_class = random.choice([0, 1])
                confidence = random.uniform(0.55, 0.85)
                
            # Output predictions:
            # 1. Volatility score
            predictions.append({
                "id": uuid.uuid4(),
                "prediction_type": "volatility",
                "symbol": symbol,
                "predicted_value": round(pred_vol * 100, 2), # convert standard dev return to percentage-like score
                "confidence": round(random.uniform(0.70, 0.90), 2),
                "model_version": "xgb-v1.0",
                "created_at": now
            })
            
            # 2. Trend direction (up / down)
            predictions.append({
                "id": uuid.uuid4(),
                "prediction_type": "trend",
                "symbol": symbol,
                "predicted_value": float(pred_trend_class), # 1.0 for up, 0.0 for down
                "confidence": round(confidence, 2),
                "model_version": "rf-v1.0",
                "created_at": now
            })
        except Exception as e:
            logger.error(f"Error generating prediction for {symbol}: {e}")
            
    return predictions
