"""
Model wrapper classes — مطابقة لما حُفظ في build_features.py.
تُستخدَم لحل مشكلة unpickling عند تحميل النماذج في سياق الـ API
(النماذج حُفظت من __main__، ونحتاج لإيجاد الـ class عند التحميل).
"""
import numpy as np


class TunedChurnModel:
    """Preprocessor + XGBoost + optimal decision threshold — bundle واحد."""
    def __init__(self, preprocessor, model, threshold: float):
        self.preprocessor = preprocessor
        self.model = model
        self.threshold = threshold

    def predict(self, X):
        X_t = self.preprocessor.transform(X)
        probs = self.model.predict_proba(X_t)[:, 1]
        return (probs >= self.threshold).astype(int)

    def predict_proba(self, X):
        X_t = self.preprocessor.transform(X)
        return self.model.predict_proba(X_t)


class TunedRegressionModel:
    """Preprocessor + XGBoost regressor — bundle واحد."""
    def __init__(self, preprocessor, model):
        self.preprocessor = preprocessor
        self.model = model

    def predict(self, X):
        X_t = self.preprocessor.transform(X)
        return self.model.predict(X_t)
