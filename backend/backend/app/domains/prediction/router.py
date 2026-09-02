from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from . import schemas, service

router = APIRouter()


@router.post(
    "/cycle",
    response_model=schemas.CyclePredictionOut,
    summary="Predict next purchase cycle",
)
async def predict_next_cycle(
    request: schemas.PredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    يتنبأ بعدد أيام الدورة القادمة لعميل + دواء محدد.

    - **is_cold_start=true**: لا يوجد تاريخ شراء كافٍ — يُستخدم default الدواء
    - **confidence**: قيمة بين 0 و1 — كلما ارتفعت كانت التنبؤ أكثر موثوقية
    """
    return await service.predict_cycle(db, request.customer_id, request.drug_id)


@router.post(
    "/churn",
    response_model=schemas.ChurnPredictionOut,
    summary="Predict churn risk for a customer-drug pair",
)
async def predict_churn_risk(
    request: schemas.PredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    يتنبأ باحتمال انقطاع العميل عن شراء دواء معيّن.

    - **churn_risk**: low / medium / high
    - **optimal_threshold**: العتبة المُستخدمة للقرار (0.33 — محسَّبة بـ Threshold Tuning)
    - **confidence**: يقين النموذج في قراره
    """
    return await service.predict_churn(db, request.customer_id, request.drug_id)


@router.post(
    "/combined",
    response_model=schemas.CombinedPredictionOut,
    summary="Get both cycle and churn predictions in one call",
)
async def predict_combined(
    request: schemas.PredictionRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    يُرجع توقع الدورة القادمة **و** احتمال الانقطاع في استدعاء API واحد.
    مفيد لـ n8n workflows التي تحتاج كلا القرارين لاختيار نوع التذكير.
    """
    return await service.predict_combined(db, request.customer_id, request.drug_id)
