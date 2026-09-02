from pydantic import BaseModel
from uuid import UUID
from typing import List


class ShapFeature(BaseModel):
    feature: str
    shap_value: float


class PredictionRequest(BaseModel):
    customer_id: UUID
    drug_id: UUID


class CyclePredictionOut(BaseModel):
    customer_id: UUID
    drug_id: UUID
    drug_name: str
    predicted_days: float
    predicted_next_date: str           # YYYY-MM-DD
    confidence: float                  # clamp(1 - MAE/avg_cycle, 0, 1)
    confidence_formula: str            # توثيق المعادلة المستخدمة
    is_cold_start: bool
    shap_top_features: List[ShapFeature]
    message: str


class ChurnPredictionOut(BaseModel):
    customer_id: UUID
    drug_id: UUID
    drug_name: str
    churn_probability: float           # من predict_proba مباشرة
    churn_risk: str                    # "low" | "medium" | "high"
    will_churn: bool                   # القرار بناءً على threshold=0.33
    confidence: float                  # = churn_probability (الاحتمالية الحقيقية)
    optimal_threshold: float           # 0.33 محسوبة بـ Threshold Tuning
    shap_top_features: List[ShapFeature]
    message: str


class CombinedPredictionOut(BaseModel):
    cycle: CyclePredictionOut
    churn: ChurnPredictionOut
