"""
Analytics Schemas — Dashboard KPIs (FR-09) + A/B Test results (FR-13)
"""
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime


# ── FR-09: Dashboard ─────────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    category: str
    order_count: int
    revenue: float
    percentage: float   # نسبة من إجمالي الطلبات


class DashboardSummary(BaseModel):
    # ── العملاء ──────────────────────────────────────────────────────────────
    total_customers: int
    active_customers_30d: int
    activity_rate_pct: float        # معدل النشاط خلال 30 يوماً

    # ── الطلبات ──────────────────────────────────────────────────────────────
    total_orders: int
    total_revenue: float
    avg_order_value: float
    orders_last_7d: int

    # ── مؤشر ML ──────────────────────────────────────────────────────────────
    regression_model_mae_days: float   # من build_features (Optuna tuned)
    total_cycles_tracked: int

    # ── توزيع الفئات ─────────────────────────────────────────────────────────
    top_drug_categories: List[CategoryBreakdown]


# ── FR-13: A/B Tests ─────────────────────────────────────────────────────────

class ABTestCreate(BaseModel):
    tenant_id: UUID
    test_name: str
    variant_a: str = "discount"
    variant_b: str = "plain"
    start_date: date
    end_date: Optional[date] = None


class ABTestOut(BaseModel):
    test_id: UUID
    tenant_id: UUID
    test_name: str
    variant_a: str
    variant_b: str
    start_date: date
    end_date: Optional[date]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ABTestVariantStats(BaseModel):
    variant: str
    sent_count: int
    converted_count: int
    conversion_rate_pct: float


class ABTestSummary(BaseModel):
    test_id: UUID
    test_name: str
    is_active: bool
    variant_a_stats: ABTestVariantStats
    variant_b_stats: ABTestVariantStats
    winner: Optional[str]   # "A" | "B" | "tie" | null (لو بيانات غير كافية)


class RecordABResultIn(BaseModel):
    test_id: UUID
    notification_id: UUID
    variant: str        # discount | plain


class MarkConvertedIn(BaseModel):
    notification_id: UUID
