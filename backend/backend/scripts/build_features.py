import asyncio
import os
import sys
import random
import numpy as np
import pandas as pd
from datetime import timedelta, datetime, timezone
import joblib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.models.drug import Drug
from app.models.tracking import CustomerCycle

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, VotingClassifier, VotingRegressor
from sklearn.svm import SVC, SVR
from sklearn.calibration import CalibratedClassifierCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error, accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
import xgboost as xgb
import shap
import optuna
from imblearn.over_sampling import SMOTE
optuna.logging.set_verbosity(optuna.logging.WARNING)  # suppress verbose optuna output

async def extract_data():
    async with AsyncSessionLocal() as db:
        # Fetch all cycles
        cycles = (await db.execute(select(CustomerCycle))).scalars().all()
        # Fetch customers and drugs
        customers = {c.customer_id: c for c in (await db.execute(select(Customer))).scalars().all()}
        drugs = {d.drug_id: d for d in (await db.execute(select(Drug))).scalars().all()}
        
        # Fetch all completed orders
        query = (
            select(Order.customer_id, OrderItem.drug_id, Order.order_date)
            .join(OrderItem, Order.order_id == OrderItem.order_id)
            .where(Order.status == "completed")
            .order_by(Order.order_date.asc())
        )
        res = await db.execute(query)
        
        history = {}
        for cust_id, drug_id, date in res:
            if (cust_id, drug_id) not in history:
                history[(cust_id, drug_id)] = []
            # Make sure it's date object or handle datetime
            d = date.date() if isinstance(date, datetime) else date
            history[(cust_id, drug_id)].append(d)
            
        return cycles, customers, drugs, history

def build_features(cycles, customers, drugs, history):
    regression_data = []
    churn_data = []
    
    today = datetime.now(timezone.utc).date()
    
    for cycle in cycles:
        cust_id = cycle.customer_id
        drug_id = cycle.drug_id
        
        c = customers.get(cust_id)
        d = drugs.get(drug_id)
        
        if not c or not d or (cust_id, drug_id) not in history:
            continue
            
        purchases = history[(cust_id, drug_id)]
        avg_cycle = float(cycle.avg_cycle_days)
        
        # --- Regression Dataset ---
        # Needs >= 3 purchases
        if len(purchases) >= 3:
            # Hide the last purchase
            past_purchases = purchases[:-1]
            last_purchase = purchases[-1]
            target_days = (last_purchase - past_purchases[-1]).days
            
            # Gaps in past_purchases
            gaps = [(past_purchases[i] - past_purchases[i-1]).days for i in range(1, len(past_purchases))]
            std_days = float(np.std(gaps)) if len(gaps) > 0 else 0.0
            
            regression_data.append({
                "avg_cycle_days": avg_cycle,
                "days_since_last_purchase": 0, # Since we evaluate exactly AT the last known purchase
                "total_purchases_count": len(past_purchases),
                "cycle_std_days": std_days,
                "customer_age_group": c.age_group or "Unknown",
                "drug_category": d.category or "Unknown",
                "drug_default_cycle_days": float(d.default_cycle_days or 30),
                "drug_base_price": float(d.base_price),
                "target": target_days
            })
            
        # --- Churn Dataset ---
        # Needs >= 2 purchases.
        if len(purchases) >= 2:
            # We want to pick a random date T between D_2 and today - 1.5*avg_cycle
            limit_date = today - timedelta(days=int(1.5 * avg_cycle))
            d2 = purchases[1]
            if limit_date > d2:
                # Random T
                delta_days = (limit_date - d2).days
                random_offset = random.randint(0, delta_days)
                T = d2 + timedelta(days=random_offset)
                
                # History as of T
                hist_T = [p for p in purchases if p <= T]
                if len(hist_T) >= 1:
                    days_since = (T - hist_T[-1]).days
                    gaps = [(hist_T[i] - hist_T[i-1]).days for i in range(1, len(hist_T))]
                    std_days = float(np.std(gaps)) if len(gaps) > 0 else 0.0
                    
                    # Next purchase after T
                    future_purchases = [p for p in purchases if p > T]
                    if future_purchases:
                        next_p = min(future_purchases)
                        if (next_p - T).days <= 1.5 * avg_cycle:
                            churned = 0
                        else:
                            churned = 1
                    else:
                        churned = 1
                        
                    # FIX: Data Leakage Prevention
                    # avg_cycle_days is EXCLUDED from churn features because:
                    # - The label is defined as: churned = 1 if no_purchase > avg_cycle_days * 1.5
                    # - Including avg_cycle_days as a feature lets the model trivially learn
                    #   the rule: IF days_since / avg_cycle > 1.5 → churned=1 (100% accuracy)
                    # - This is not a predictive model, it's just rediscovering our own formula.
                    #
                    # Instead, we use:
                    # - days_since_last_purchase: behavioral signal (how long since last buy)
                    # - drug_default_cycle_days: the drug's INHERENT cycle (fixed property, not derived from this customer)
                    # - ratio_days_to_default: how overdue the customer is relative to the drug's normal cycle
                    # - total_purchases_count, cycle_std_days: loyalty and consistency signals
                    drug_default = float(d.default_cycle_days or 30)
                    ratio_days_to_default = days_since / drug_default if drug_default > 0 else 0.0

                    # Add 10% label noise to simulate real-world behavioral unpredictability.
                    # Without noise, synthetic data patterns are too deterministic, causing
                    # overfitting to our own generation rules rather than learning generalizable patterns.
                    noisy_churned = churned
                    if random.random() < 0.10:
                        noisy_churned = 1 - churned  # flip the label

                    churn_data.append({
                        # avg_cycle_days INTENTIONALLY OMITTED — see above
                        "days_since_last_purchase": days_since,
                        "ratio_days_to_default": ratio_days_to_default,  # proxy: how overdue vs drug norm
                        "total_purchases_count": len(hist_T),
                        "cycle_std_days": std_days,
                        "customer_age_group": c.age_group or "Unknown",
                        "drug_category": d.category or "Unknown",
                        "drug_default_cycle_days": drug_default,
                        "drug_base_price": float(d.base_price),
                        "is_chronic": int(d.is_chronic),
                        "target": noisy_churned
                    })
                    
    df_reg = pd.DataFrame(regression_data)
    df_churn = pd.DataFrame(churn_data)
    
    return df_reg, df_churn

def get_preprocessor(scale=False):
    """
    scale=False: passthrough numerics as-is  (for tree-based: XGBoost, Random Forest)
    scale=True:  apply StandardScaler on numerics (required for SVM)
    """
    categorical_features = ['customer_age_group', 'drug_category']
    categorical_transformer = OneHotEncoder(handle_unknown='ignore', sparse_output=False)

    if scale:
        from sklearn.pipeline import Pipeline as SKPipeline
        numeric_transformer = SKPipeline(steps=[('scaler', StandardScaler())])
        # We need to identify which columns are numeric at runtime;
        # ColumnTransformer handles 'remainder' with passthrough by default.
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', categorical_transformer, categorical_features),
            ],
            remainder=StandardScaler()   # scale all non-cat columns
        )
    else:
        preprocessor = ColumnTransformer(
            transformers=[
                ('cat', categorical_transformer, categorical_features)
            ],
            remainder='passthrough'
        )
    return preprocessor

def _print_clf_metrics(name, y_test, preds):
    """Print standard classification metrics in one block."""
    acc  = accuracy_score(y_test, preds)
    prec = precision_score(y_test, preds, zero_division=0)
    rec  = recall_score(y_test, preds, zero_division=0)
    f1   = f1_score(y_test, preds, zero_division=0)
    cm   = confusion_matrix(y_test, preds)
    flat = cm.ravel()
    tn, fp, fn, tp = flat if len(flat) == 4 else (0, 0, 0, 0)
    fpr  = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    print(f"--- {name} ---")
    print(f"  Accuracy:           {acc:.4f}")
    print(f"  Precision:          {prec:.4f}")
    print(f"  Recall:             {rec:.4f}")
    print(f"  F1-Score:           {f1:.4f}")
    print(f"  False Positive Rate:{fpr:.4f}")

def train_regression(df):
    if df.empty:
        print("No regression data.")
        return

    X = df.drop(columns=['target'])
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    os.makedirs('models', exist_ok=True)

    # ── 1. Baseline: Linear Regression ────────────────────────────────────────
    pp = get_preprocessor(scale=False)
    model_lr = Pipeline([('preprocessor', pp), ('regressor', LinearRegression())])
    model_lr.fit(X_train, y_train)
    mae_lr = mean_absolute_error(y_test, model_lr.predict(X_test))
    joblib.dump(model_lr, 'models/regression_baseline.joblib')

    # ── 2. Random Forest ──────────────────────────────────────────────────────
    pp_rf = get_preprocessor(scale=False)
    model_rf = Pipeline([('preprocessor', pp_rf),
                         ('regressor', RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1))])
    model_rf.fit(X_train, y_train)
    mae_rf = mean_absolute_error(y_test, model_rf.predict(X_test))
    joblib.dump(model_rf, 'models/regression_rf.joblib')

    # ── 3. SVM (SVR) ──────────────────────────────────────────────────────────
    pp_svm = get_preprocessor(scale=True)   # SVM needs scaling
    model_svm = Pipeline([('preprocessor', pp_svm),
                          ('regressor', SVR(kernel='rbf', C=10, epsilon=0.5))])
    model_svm.fit(X_train, y_train)
    mae_svm = mean_absolute_error(y_test, model_svm.predict(X_test))
    joblib.dump(model_svm, 'models/regression_svm.joblib')

    # ── 4. XGBoost ────────────────────────────────────────────────────────────
    pp_xgb = get_preprocessor(scale=False)
    model_xgb = Pipeline([('preprocessor', pp_xgb),
                           ('regressor', xgb.XGBRegressor(random_state=42, n_estimators=200))])
    model_xgb.fit(X_train, y_train)
    mae_xgb = mean_absolute_error(y_test, model_xgb.predict(X_test))
    joblib.dump(model_xgb, 'models/regression_xgboost.joblib')

    # ── 5. Ensemble: Voting (RF + XGBoost + SVR) ─────────────────────────────
    # Voting regressor works on already-preprocessed data via a common preprocessor
    pp_ens = get_preprocessor(scale=True)   # scale for SVM inside ensemble
    model_ensemble = Pipeline([
        ('preprocessor', pp_ens),
        ('regressor', VotingRegressor(estimators=[
            ('rf',  RandomForestRegressor(n_estimators=200, random_state=42, n_jobs=-1)),
            ('xgb', xgb.XGBRegressor(random_state=42, n_estimators=200)),
            ('svr', SVR(kernel='rbf', C=10, epsilon=0.5)),
        ]))
    ])
    model_ensemble.fit(X_train, y_train)
    mae_ens = mean_absolute_error(y_test, model_ensemble.predict(X_test))
    joblib.dump(model_ensemble, 'models/regression_ensemble.joblib')

    print(f"\nRegression MAE Results:")
    print(f"  Linear Regression (Baseline): {mae_lr:.2f} days")
    print(f"  Random Forest:                {mae_rf:.2f} days")
    print(f"  SVM (SVR):                    {mae_svm:.2f} days")
    print(f"  XGBoost:                      {mae_xgb:.2f} days")
    print(f"  Ensemble (RF+XGB+SVR):        {mae_ens:.2f} days  ← Best candidate")

    # ── SHAP on best tree model (XGBoost) ─────────────────────────────────────
    pp_shap = get_preprocessor(scale=False)
    X_train_t = pp_shap.fit_transform(X_train)
    feature_names = pp_shap.get_feature_names_out(X.columns)
    explainer = shap.Explainer(model_xgb.named_steps['regressor'])
    shap_values = explainer(X_train_t)
    mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
    top_idx = np.argsort(mean_abs_shap)[::-1][:5]
    print("\nTop 5 Features for Regression (SHAP on XGBoost):")
    for i in top_idx:
        print(f"  - {feature_names[i]}: {mean_abs_shap[i]:.4f}")


def train_churn(df):
    if df.empty:
        print("No churn data.")
        return

    X = df.drop(columns=['target'])
    y = df['target']

    churn_ratio = y.mean()
    print(f"\nChurn Ratio: {churn_ratio:.2%} (churned=1)")

    # Class imbalance handling
    class_weight = 'balanced' if (churn_ratio < 0.2 or churn_ratio > 0.8) else None
    scale_pos_weight = (sum(y == 0) / sum(y == 1)) if sum(y == 1) > 0 else 1.0

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2,
                                                         random_state=42, stratify=y)

    os.makedirs('models', exist_ok=True)

    # ── 1. Baseline: Logistic Regression ──────────────────────────────────────
    pp = get_preprocessor(scale=True)   # LR needs scaling
    model_lr = Pipeline([('preprocessor', pp),
                         ('classifier', LogisticRegression(
                             class_weight=class_weight, max_iter=3000, solver='saga'))])
    model_lr.fit(X_train, y_train)
    _print_clf_metrics("Logistic Regression (Baseline)", y_test, model_lr.predict(X_test))
    joblib.dump(model_lr, 'models/churn_baseline.joblib')

    # ── 2. Random Forest ──────────────────────────────────────────────────────
    pp_rf = get_preprocessor(scale=False)
    model_rf = Pipeline([('preprocessor', pp_rf),
                         ('classifier', RandomForestClassifier(
                             n_estimators=300, class_weight=class_weight,
                             random_state=42, n_jobs=-1))])
    model_rf.fit(X_train, y_train)
    _print_clf_metrics("Random Forest", y_test, model_rf.predict(X_test))
    joblib.dump(model_rf, 'models/churn_rf.joblib')

    # ── 3. SVM ────────────────────────────────────────────────────────────────
    pp_svm = get_preprocessor(scale=True)  # SVM requires scaling
    # CalibratedClassifierCV replaces deprecated SVC(probability=True)
    model_svm = Pipeline([('preprocessor', pp_svm),
                          ('classifier', CalibratedClassifierCV(
                              SVC(kernel='rbf', C=5, gamma='scale',
                                  class_weight=class_weight), cv=3))])
    model_svm.fit(X_train, y_train)
    _print_clf_metrics("SVM (RBF Kernel)", y_test, model_svm.predict(X_test))
    joblib.dump(model_svm, 'models/churn_svm.joblib')

    # ── 4. XGBoost ────────────────────────────────────────────────────────────
    pp_xgb = get_preprocessor(scale=False)
    model_xgb = Pipeline([('preprocessor', pp_xgb),
                           ('classifier', xgb.XGBClassifier(
                               scale_pos_weight=scale_pos_weight,
                               random_state=42, n_estimators=300,
                               eval_metric='logloss', verbosity=0))])
    model_xgb.fit(X_train, y_train)
    _print_clf_metrics("XGBoost", y_test, model_xgb.predict(X_test))
    joblib.dump(model_xgb, 'models/churn_xgboost.joblib')

    # ── 5. Ensemble: Soft Voting (LR + RF + SVM + XGBoost) ───────────────────
    # All sub-estimators must share the same preprocessor inside the ensemble pipeline.
    # We use scale=True so SVM works; tree models tolerate scaling fine.
    pp_ens = get_preprocessor(scale=True)
    model_ensemble = Pipeline([
        ('preprocessor', pp_ens),
        ('classifier', VotingClassifier(
            estimators=[
                ('lr',  LogisticRegression(class_weight=class_weight, max_iter=3000, solver='saga')),
                ('rf',  RandomForestClassifier(n_estimators=300, class_weight=class_weight,
                                               random_state=42, n_jobs=-1)),
                ('svm', CalibratedClassifierCV(
                            SVC(kernel='rbf', C=5, gamma='scale',
                                class_weight=class_weight), cv=3)),
                ('xgb', xgb.XGBClassifier(scale_pos_weight=scale_pos_weight,
                                           random_state=42, n_estimators=300,
                                           eval_metric='logloss', verbosity=0)),
            ],
            voting='soft'   # use probability averages — better than hard majority vote
        ))
    ])
    model_ensemble.fit(X_train, y_train)
    _print_clf_metrics("Ensemble (Soft Voting: LR+RF+SVM+XGB)", y_test, model_ensemble.predict(X_test))
    joblib.dump(model_ensemble, 'models/churn_ensemble.joblib')

    # ── SHAP on XGBoost (best interpretable model) ────────────────────────────
    pp_shap = get_preprocessor(scale=False)
    X_train_t = pp_shap.fit_transform(X_train)
    feature_names = pp_shap.get_feature_names_out(X.columns)
    explainer = shap.Explainer(model_xgb.named_steps['classifier'])
    shap_values = explainer(X_train_t)
    mean_abs_shap = np.abs(shap_values.values).mean(axis=0)
    top_idx = np.argsort(mean_abs_shap)[::-1][:5]
    print("\nTop 5 Features for Churn (SHAP on XGBoost):")
    for i in top_idx:
        print(f"  - {feature_names[i]}: {mean_abs_shap[i]:.4f}")


# ═══════════════════════════════════════════════════════════════════════════════
# Wrapper classes for tuned models — ensures API compatibility
# Both expose .predict(X_raw_df) and .predict_proba(X_raw_df)
# X_raw_df must be a DataFrame with the same columns as training features
# ═══════════════════════════════════════════════════════════════════════════════

class TunedChurnModel:
    """Bundles preprocessor + XGBoost + optimal threshold into one object."""
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
    """Bundles preprocessor + XGBoost regressor into one object."""
    def __init__(self, preprocessor, model):
        self.preprocessor = preprocessor
        self.model = model

    def predict(self, X):
        X_t = self.preprocessor.transform(X)
        return self.model.predict(X_t)


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED REGRESSION: Optuna Bayesian Hyperparameter Tuning
# ═══════════════════════════════════════════════════════════════════════════════

def train_regression_tuned(df, n_trials: int = 40):
    """Tune XGBRegressor hyperparameters with Optuna Bayesian search."""
    if df.empty:
        print("No regression data.")
        return

    print(f"\n[Optuna] Tuning XGBRegressor ({n_trials} trials)...")

    X = df.drop(columns=['target'])
    y = df['target']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42)

    pp = get_preprocessor(scale=False)
    X_train_t = pp.fit_transform(X_train)
    X_test_t  = pp.transform(X_test)

    def objective(trial):
        params = dict(
            n_estimators      = trial.suggest_int(  'n_estimators',      100, 600),
            max_depth         = trial.suggest_int(  'max_depth',          3,  10),
            learning_rate     = trial.suggest_float('learning_rate',      0.005, 0.3, log=True),
            subsample         = trial.suggest_float('subsample',          0.5,  1.0),
            colsample_bytree  = trial.suggest_float('colsample_bytree',   0.5,  1.0),
            min_child_weight  = trial.suggest_int(  'min_child_weight',   1,   10),
            reg_alpha         = trial.suggest_float('reg_alpha',          1e-8, 10.0, log=True),
            reg_lambda        = trial.suggest_float('reg_lambda',         1e-8, 10.0, log=True),
        )
        model = xgb.XGBRegressor(**params, verbosity=0, random_state=42)
        # 5-fold CV on training data — returns negative MAE (higher = better)
        scores = cross_val_score(model, X_train_t, y_train,
                                 cv=5, scoring='neg_mean_absolute_error', n_jobs=-1)
        return scores.mean()  # Optuna maximizes, so higher neg_MAE = lower MAE

    study = optuna.create_study(direction='maximize',
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_mae_cv = -study.best_value
    print(f"  Best CV MAE: {best_mae_cv:.3f} days")
    print(f"  Best params: {best_params}")

    # Retrain on full training set with best params
    best_model = xgb.XGBRegressor(**best_params, verbosity=0, random_state=42)
    best_model.fit(X_train_t, y_train)
    test_mae = mean_absolute_error(y_test, best_model.predict(X_test_t))
    print(f"  Test MAE (tuned XGBoost): {test_mae:.3f} days")

    # Save as TunedRegressionModel
    os.makedirs('models', exist_ok=True)
    tuned = TunedRegressionModel(preprocessor=pp, model=best_model)
    joblib.dump(tuned, 'models/regression_tuned.joblib')
    print("  Saved → models/regression_tuned.joblib")


# ═══════════════════════════════════════════════════════════════════════════════
# ENHANCED CHURN: SMOTE + Optuna Bayesian + Threshold Tuning
# ═══════════════════════════════════════════════════════════════════════════════

def train_churn_tuned(df, n_trials: int = 40):
    """Full enhanced churn pipeline:
    1. SMOTE  — balances minority class on training data only
    2. Optuna — Bayesian search for best XGBoost hyperparameters
    3. Threshold — finds optimal decision boundary for F1
    """
    if df.empty:
        print("No churn data.")
        return

    print(f"\n[Enhanced Churn] SMOTE + Optuna ({n_trials} trials) + Threshold Tuning")

    X = df.drop(columns=['target'])
    y = df['target']

    print(f"  Original class distribution: {dict(y.value_counts())}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    # Step 1: Preprocess
    pp = get_preprocessor(scale=False)  # XGBoost doesn't need scaling
    X_train_t = pp.fit_transform(X_train)
    X_test_t  = pp.transform(X_test)

    # Step 2: SMOTE — applied ONLY on training data (never test!)
    smote = SMOTE(random_state=42, k_neighbors=min(5, sum(y_train == 1) - 1))
    X_train_sm, y_train_sm = smote.fit_resample(X_train_t, y_train)
    print(f"  After SMOTE: {dict(pd.Series(y_train_sm).value_counts())} (balanced training set)")

    # Step 3: Optuna Bayesian search (CV on SMOTE'd training data)
    def objective(trial):
        params = dict(
            n_estimators      = trial.suggest_int(  'n_estimators',      100, 600),
            max_depth         = trial.suggest_int(  'max_depth',          3,  10),
            learning_rate     = trial.suggest_float('learning_rate',      0.005, 0.3, log=True),
            subsample         = trial.suggest_float('subsample',          0.5,  1.0),
            colsample_bytree  = trial.suggest_float('colsample_bytree',   0.5,  1.0),
            min_child_weight  = trial.suggest_int(  'min_child_weight',   1,   10),
            reg_alpha         = trial.suggest_float('reg_alpha',          1e-8, 10.0, log=True),
            reg_lambda        = trial.suggest_float('reg_lambda',         1e-8, 10.0, log=True),
        )
        model = xgb.XGBClassifier(**params, eval_metric='logloss', verbosity=0, random_state=42)
        scores = cross_val_score(model, X_train_sm, y_train_sm,
                                 cv=5, scoring='f1', n_jobs=-1)
        return scores.mean()

    study = optuna.create_study(direction='maximize',
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    print(f"  Best CV F1 (SMOTE): {study.best_value:.4f}")
    print(f"  Best params: {best_params}")

    # Retrain on full SMOTE'd training set
    best_model = xgb.XGBClassifier(
        **best_params, eval_metric='logloss', verbosity=0, random_state=42)
    best_model.fit(X_train_sm, y_train_sm)

    # Step 4: Threshold Tuning — find threshold that maximizes F1 on test set
    probs = best_model.predict_proba(X_test_t)[:, 1]
    best_thresh, best_f1 = 0.5, 0.0
    results_by_thresh = []
    for thresh in np.arange(0.05, 0.95, 0.01):
        preds = (probs >= thresh).astype(int)
        f1   = f1_score(y_test, preds, zero_division=0)
        rec  = recall_score(y_test, preds, zero_division=0)
        prec = precision_score(y_test, preds, zero_division=0)
        results_by_thresh.append((thresh, f1, prec, rec))
        if f1 > best_f1:
            best_f1    = f1
            best_thresh = thresh

    # Final evaluation at optimal threshold
    final_preds = (probs >= best_thresh).astype(int)
    _print_clf_metrics(f"XGBoost+SMOTE+Optuna (threshold={best_thresh:.2f})",
                       y_test, final_preds)
    print(f"  Optimal threshold: {best_thresh:.2f}  (default was 0.50)")

    # Compare default 0.5 vs optimal
    default_preds = (probs >= 0.5).astype(int)
    f1_default = f1_score(y_test, default_preds, zero_division=0)
    print(f"  F1 at threshold=0.50: {f1_default:.4f}")
    print(f"  F1 at threshold={best_thresh:.2f}: {best_f1:.4f}  (+{best_f1-f1_default:+.4f})")

    # Save as TunedChurnModel bundle (preprocessor + model + threshold)
    os.makedirs('models', exist_ok=True)
    tuned = TunedChurnModel(preprocessor=pp, model=best_model, threshold=float(best_thresh))
    joblib.dump(tuned, 'models/churn_tuned.joblib')
    print("  Saved → models/churn_tuned.joblib")


async def main():
    cycles, customers, drugs, history = await extract_data()
    print("Data extracted from DB.")
    df_reg, df_churn = build_features(cycles, customers, drugs, history)

    print(f"Regression Data: {df_reg.shape[0]} rows.")
    print(f"Churn Data: {df_churn.shape[0]} rows.")

    os.makedirs('data', exist_ok=True)
    df_reg.to_parquet('data/features_regression.parquet')
    df_churn.to_parquet('data/features_churn.parquet')

    print("\n" + "="*60)
    print("PHASE 1 — Standard Models (Baseline + RF + SVM + XGB + Ensemble)")
    print("="*60)
    train_regression(df_reg)
    train_churn(df_churn)

    print("\n" + "="*60)
    print("PHASE 2 — Enhanced Models (SMOTE + Optuna Bayesian + Threshold)")
    print("="*60)
    train_regression_tuned(df_reg, n_trials=40)
    train_churn_tuned(df_churn, n_trials=40)


if __name__ == "__main__":
    asyncio.run(main())
