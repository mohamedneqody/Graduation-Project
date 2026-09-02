"""
Prediction Service — تنبؤ بالدورة القادمة والانقطاع مع Explainability (SHAP).

قرارات تصميمية موثقة:
─────────────────────────────────────────────────────────────────────────────
1. Confidence للـ Regression (معادلة مصممة، غير قياسية):
   confidence = clamp(1 - MAE / avg_cycle_days, 0, 1)
   المنطق: نسبة الخطأ المتوقع (MAE=3.27 يوم) مقارنة بطول الدورة ذاتها.
   دورة طويلة (60 يوم) → خطأ 3 أيام نسبته 5% → ثقة 95%.
   دورة قصيرة (7 أيام) → خطأ 3 أيام نسبته 43% → ثقة 57%.
   [قرار تصميمي — ليس معياراً قياسياً]

2. Confidence للـ Churn:
   confidence = churn_probability من predict_proba مباشرة.
   هذا هو الاحتمالي الحقيقي المُعايَر بـ SMOTE + Optuna — لا حاجة لمعادلة بديلة.

3. SHAP TreeExplainer:
   يُطبَّق على النموذج الداخلي (model.model) بعد تحويل الـ features بالـ preprocessor،
   ويُرجَع أفضل 3 features فقط لكل تنبؤ فردي (Explainability مطلوب في SAD + PRD).
─────────────────────────────────────────────────────────────────────────────
"""
import pickle
import numpy as np
import pandas as pd
import shap
from pathlib import Path
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle
from app.core.exceptions import NotFoundError
from . import schemas

# ── المسارات ─────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent.parent.parent
MODELS_DIR = BASE_DIR / "models"

# MAE من آخر تدريب (Optuna Tuned XGBoost Regressor)
REGRESSION_MAE_DAYS: float = 3.27

# ── Model Cache ───────────────────────────────────────────────────────────
_model_cache: dict = {}


import sys
import joblib

def _load(model_name: str):
    if model_name not in _model_cache:
        path = MODELS_DIR / f"{model_name}.joblib"
        if not path.exists():
            raise FileNotFoundError(f"Model file not found: {path}")
        
        # Injection to allow loading classes saved from __main__
        from app.domains.prediction import model_wrappers
        if "TunedRegressionModel" in dir(model_wrappers):
            sys.modules["__main__"].TunedRegressionModel = model_wrappers.TunedRegressionModel
        if "TunedChurnModel" in dir(model_wrappers):
            sys.modules["__main__"].TunedChurnModel = model_wrappers.TunedChurnModel

        _model_cache[model_name] = joblib.load(path)
    return _model_cache[model_name]


# ── SHAP Helper ───────────────────────────────────────────────────────────

def _get_shap_top3(
    bundle,          # TunedRegressionModel أو TunedChurnModel
    df: pd.DataFrame,
    top_n: int = 3,
) -> List[schemas.ShapFeature]:
    """
    يحسب SHAP values لتنبؤ واحد ويُرجع أعلى top_n features تأثيراً.
    يستخدم TreeExplainer على النموذج الداخلي بعد تطبيق الـ preprocessor.
    """
    try:
        X_transformed = bundle.preprocessor.transform(df)
        explainer = shap.TreeExplainer(bundle.model)
        shap_values = explainer.shap_values(X_transformed)

        # للـ Churn (XGBClassifier مع SMOTE): shap_values قد يكون list أو 2D array
        if isinstance(shap_values, list):
            # Binary classifier: index 1 = positive class (churn)
            sv = np.abs(shap_values[1][0])
        else:
            sv = np.abs(shap_values[0] if shap_values.ndim > 1 else shap_values)

        # أسماء الـ features بعد الـ preprocessing
        feature_names = bundle.preprocessor.get_feature_names_out()
        top_idx = np.argsort(sv)[::-1][:top_n]

        return [
            schemas.ShapFeature(
                feature=str(feature_names[i]).replace("remainder__", "").replace("cat__", ""),
                shap_value=round(float(sv[i]), 4),
            )
            for i in top_idx
        ]
    except Exception:
        # SHAP غير ضروري للاستجابة — لا نوقف الـ API لو فشل
        return []


# ── استخراج الـ Features ──────────────────────────────────────────────────

async def _build_features(
    db: AsyncSession, customer_id: UUID, drug_id: UUID
) -> dict:
    """يجلب بيانات العميل/الدواء/الدورة ويبني dict الـ features للنموذجين."""

    drug_res = await db.execute(select(Drug).where(Drug.drug_id == drug_id))
    drug = drug_res.scalars().first()
    if not drug:
        raise NotFoundError("Drug", str(drug_id))

    cust_res = await db.execute(select(Customer).where(Customer.customer_id == customer_id))
    customer = cust_res.scalars().first()
    if not customer:
        raise NotFoundError("Customer", str(customer_id))

    cycle_res = await db.execute(
        select(CustomerCycle).where(
            CustomerCycle.customer_id == customer_id,
            CustomerCycle.drug_id == drug_id,
        )
    )
    cycle = cycle_res.scalars().first()

    history_res = await db.execute(
        select(Order.order_date)
        .join(OrderItem, Order.order_id == OrderItem.order_id)
        .where(
            Order.customer_id == customer_id,
            OrderItem.drug_id == drug_id,
            Order.status == "completed",
        )
        .order_by(Order.order_date)
    )
    purchase_dates = [row[0] for row in history_res.all()]

    now = datetime.now(timezone.utc)
    drug_default = float(drug.default_cycle_days or 30)
    is_cold_start = cycle is None or len(purchase_dates) < 2

    if is_cold_start:
        avg_cycle = drug_default
        std_days = 0.0
        total_purchases = max(1, len(purchase_dates))
        days_since = int(drug_default)
        if purchase_dates:
            last = purchase_dates[-1]
            if hasattr(last, "tzinfo") and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            days_since = (now - last).days
    else:
        avg_cycle = float(cycle.avg_cycle_days)
        total_purchases = len(purchase_dates)
        last = purchase_dates[-1]
        if hasattr(last, "tzinfo") and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        days_since = (now - last).days

        gaps = []
        for i in range(1, len(purchase_dates)):
            d1, d2 = purchase_dates[i - 1], purchase_dates[i]
            if hasattr(d1, "tzinfo") and d1.tzinfo is None:
                d1 = d1.replace(tzinfo=timezone.utc)
            if hasattr(d2, "tzinfo") and d2.tzinfo is None:
                d2 = d2.replace(tzinfo=timezone.utc)
            gaps.append(abs((d2 - d1).days))
        std_days = float(np.std(gaps)) if gaps else 0.0

    ratio = days_since / avg_cycle if avg_cycle > 0 else 1.0

    return {
        "is_cold_start": is_cold_start,
        "drug_name":     drug.name,
        "avg_cycle":     avg_cycle,
        "features": {
            "avg_cycle_days":           avg_cycle,
            "days_since_last_purchase": days_since,
            "ratio_days_to_default":    round(ratio, 4),
            "total_purchases_count":    total_purchases,
            "cycle_std_days":           round(std_days, 2),
            "customer_age_group":       customer.age_group or "Unknown",
            "drug_category":            drug.category or "Unknown",
            "drug_default_cycle_days":  drug_default,
            "drug_base_price":          float(drug.base_price),
            "is_chronic":               int(drug.is_chronic),
        },
    }


# ── Prediction Functions ──────────────────────────────────────────────────

async def predict_cycle(
    db: AsyncSession, customer_id: UUID, drug_id: UUID
) -> schemas.CyclePredictionOut:
    data    = await _build_features(db, customer_id, drug_id)
    features  = data["features"]
    avg_cycle = data["avg_cycle"]
    is_cs     = data["is_cold_start"]

    model = _load("regression_tuned")
    df    = pd.DataFrame([features])

    predicted_days = float(model.predict(df)[0])
    predicted_days = max(1.0, round(predicted_days, 1))

    # ── Confidence (معادلة مصممة — انظر تعليق أعلى الملف) ─────────────
    # confidence = clamp(1 - MAE / avg_cycle_days, 0, 1)
    if is_cs:
        confidence = 0.40          # cold-start دائماً ثقة منخفضة
    elif avg_cycle > 0:
        raw = 1.0 - REGRESSION_MAE_DAYS / avg_cycle
        confidence = round(max(0.0, min(1.0, raw)), 3)
    else:
        confidence = 0.50

    shap_features = _get_shap_top3(model, df)
    next_date = (
        datetime.now(timezone.utc) + timedelta(days=predicted_days)
    ).strftime("%Y-%m-%d")

    return schemas.CyclePredictionOut(
        customer_id=customer_id,
        drug_id=drug_id,
        drug_name=data["drug_name"],
        predicted_days=predicted_days,
        predicted_next_date=next_date,
        confidence=confidence,
        confidence_formula="1 - (MAE={mae} / avg_cycle={avg})".format(
            mae=REGRESSION_MAE_DAYS, avg=round(avg_cycle, 1)
        ),
        is_cold_start=is_cs,
        shap_top_features=shap_features,
        message=(
            "Cold-start: insufficient history — using drug default cycle"
            if is_cs
            else "Prediction based on personal purchase history"
        ),
    )


async def predict_churn(
    db: AsyncSession, customer_id: UUID, drug_id: UUID
) -> schemas.ChurnPredictionOut:
    data     = await _build_features(db, customer_id, drug_id)
    features = data["features"]
    is_cs    = data["is_cold_start"]

    model = _load("churn_tuned")

    # أزل avg_cycle_days — حُذف من features الـ Churn لإصلاح Data Leakage
    churn_features = {k: v for k, v in features.items() if k != "avg_cycle_days"}
    df = pd.DataFrame([churn_features])

    probs      = model.predict_proba(df)[:, 1]
    churn_prob = float(probs[0])
    will_churn = bool(model.predict(df)[0])
    threshold  = float(model.threshold)  # 0.33 المُحسَّب بـ Threshold Tuning

    # ── Confidence = احتمالية predict_proba مباشرة ──────────────────────
    # هذه هي القيمة الحقيقية المُعايَرة — لا حاجة لمعادلة مشتقة.
    confidence = round(churn_prob, 4)

    # ── Risk Tiers ───────────────────────────────────────────────────────
    # <0.33 → low (أقل من عتبة القرار)
    # 0.33–0.60 → medium
    # >0.60 → high
    if churn_prob >= 0.60:
        risk = "high"
        action = "Action Required — send personalized reminder with incentive"
    elif churn_prob >= 0.33:
        risk = "medium"
        action = "Monitor — consider soft reminder in next cycle"
    else:
        risk = "low"
        action = "No action needed — customer engagement is healthy"

    shap_features = _get_shap_top3(model, df)

    return schemas.ChurnPredictionOut(
        customer_id=customer_id,
        drug_id=drug_id,
        drug_name=data["drug_name"],
        churn_probability=round(churn_prob, 4),
        churn_risk=risk,
        will_churn=will_churn,
        confidence=confidence,
        optimal_threshold=threshold,
        shap_top_features=shap_features,
        message=action,
    )


async def predict_combined(
    db: AsyncSession, customer_id: UUID, drug_id: UUID
) -> schemas.CombinedPredictionOut:
    cycle = await predict_cycle(db, customer_id, drug_id)
    churn = await predict_churn(db, customer_id, drug_id)
    return schemas.CombinedPredictionOut(cycle=cycle, churn=churn)
