import io
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.drug import Drug
from app.models.customer import Customer
from app.core.rate_limit import limiter
from app.dependencies.auth import require_role, get_current_user
from pydantic import BaseModel
from . import schemas, service
from .copilot_draft import CopilotDraftEngine

# ReportLab & Arabic imports for PDF export
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    try:
        pdfmetrics.registerFont(TTFont('Arabic', 'C:/Windows/Fonts/arial.ttf'))
        pdfmetrics.registerFont(TTFont('Arabic-Bold', 'C:/Windows/Fonts/arialbd.ttf'))
    except Exception:
        pass
    HAS_PDF_LIBS = True
except ImportError:
    HAS_PDF_LIBS = False

router = APIRouter()


@router.post(
    "/chat",
    response_model=schemas.AIChatResponse,
    summary="Chat with the pharmacy AI bot (Hybrid RAG)",
)
@limiter.limit("60/minute")
async def chat_with_ai(
    request: Request,
    body: schemas.AIChatRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await service.generate_ai_response(
        message=body.message,
        db=db,
        session_id=body.session_id,
        history=body.history,
    )
    return result


@router.post(
    "/copilot/draft",
    summary="Generate Pharmacist Copilot Response Draft (Human-in-the-Loop)",
)
@limiter.limit("10/minute")
async def generate_pharmacist_draft_endpoint(
    request: Request,
    body: schemas.CopilotDraftRequest,
    _staff=Depends(require_role("admin", "pharmacist", "super_admin")),
):
    draft = await CopilotDraftEngine.generate_pharmacist_draft(
        customer_name=body.customer_name,
        conversation_history=body.conversation_history,
        escalation_reason=body.escalation_reason,
    )
    return draft


class PatientHealthInsightRequest(BaseModel):
    orders: Optional[List[Dict[str, Any]]] = None

@router.post(
    "/patient-health-insights",
    summary="Secure backend proxy for patient health insights (via n8n Patient Health Agent)",
)
@limiter.limit("10/minute")
async def get_patient_health_insights(
    request: Request,
    body: PatientHealthInsightRequest,
    current_user: Customer = Depends(get_current_user),
):
    import httpx
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(
                "http://127.0.0.1:5678/webhook/aicos-patient-health",
                json={
                    "customer_id": str(current_user.customer_id),
                    "customer_name": current_user.full_name or current_user.email.split("@")[0],
                    "email": current_user.email,
                    "orders": body.orders or [],
                }
            )
            if res.status_code == 200:
                return res.json()
            return {"message": "Health insights currently unavailable."}
    except Exception:
        return {"message": "Health insights service temporarily unreachable."}


@router.post(
    "/upload-prescription-chat",
    summary="Upload and analyze prescription image directly inside the chat",
)
@limiter.limit("10/minute")
async def upload_prescription_chat(
    request: Request,
    file: UploadFile = File(...),
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="يُرجى رفع ملف صورة صالح للروشتة (JPG / PNG)."
        )

    # 5MB File size limit check to prevent storage DoS
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    content = await file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="حجم صورة الروشتة يتجاوز الحد الأقصى المسموح به (5 ميجابايت)."
        )

    # Honest medical feedback: Acknowledge receipt without fabricating medications
    return {
        "status": "success",
        "filename": file.filename,
        "message": f"تم استلام صورة الروشتة ({file.filename}) بنجاح. يمكنك إرسالها لمراجعة الصيدلي السريري المباشرة عبر قسم الروشتات، أو كتابة اسم الدواء في المحادثة للبحث الفوري عنه.",
        "detected_drugs": [],
        "total_price": 0.0,
        "requires_pharmacist_review": True
    }


@router.post(
    "/export-summary-pdf",
    summary="Export patient consultation and drug price summary as branded PDF",
)
@limiter.limit("5/minute")
async def export_consultation_summary_pdf(
    request: Request,
    body: schemas.ExportPdfRequest,
    current_user: Customer = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not HAS_PDF_LIBS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="مكتبات توليد ملفات PDF غير متوفرة حالياً."
        )

    def ar(text: str) -> str:
        if not text:
            return ""
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=30,
        leftMargin=30,
        topMargin=25,
        bottomMargin=25
    )

    story = []

    title_style = ParagraphStyle(
        'ArTitle',
        fontName='Arabic-Bold',
        fontSize=15,
        leading=20,
        alignment=1,
        textColor=colors.HexColor('#0f766e')
    )
    sub_style = ParagraphStyle(
        'ArSub',
        fontName='Arabic',
        fontSize=10,
        leading=14,
        alignment=1,
        textColor=colors.HexColor('#334155')
    )
    cell_style = ParagraphStyle(
        'ArCell',
        fontName='Arabic',
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor('#0f172a')
    )
    cell_bold = ParagraphStyle(
        'ArCellB',
        fontName='Arabic-Bold',
        fontSize=10,
        leading=14,
        alignment=2,
        textColor=colors.HexColor('#0f766e')
    )

    # 1. Header
    header_data = [
        [Paragraph(ar("صيدلية AI-COS الذكية — ملخص الاستشارة الطبية والأسعار"), title_style)],
        [Paragraph(ar("جامعة بورسعيد — كلية تكنولوجيا الإدارة ونظم المعلومات (BIS / MTIS)"), sub_style)],
        [Paragraph(ar(f"اسم العميل: {body.customer_name} | التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}"), sub_style)],
    ]
    t_header = Table(header_data, colWidths=[535])
    t_header.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdfa')),
        ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#0f766e')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_header)
    story.append(Spacer(1, 14))

    # 2. Consultation Dialogue & Summary Notes
    if body.chat_history and len(body.chat_history) > 0:
        table_rows = [
            [
                Paragraph(ar("تفاصيل الاستشارة والإرشادات المقدمة"), cell_bold),
                Paragraph(ar("الطرف"), cell_bold)
            ]
        ]
        for msg in body.chat_history[-6:]:
            role_label = "المريض" if msg.get("role") == "user" else "صيدلي الذكاء الاصطناعي"
            txt = msg.get("content") or msg.get("text") or ""
            table_rows.append([
                Paragraph(ar(txt[:300]), cell_style),
                Paragraph(ar(role_label), cell_bold)
            ])
        t_drugs = Table(table_rows, colWidths=[420, 115])
        t_drugs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e0f2fe')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
    else:
        table_rows = [
            [Paragraph(ar("استشارة صيدلانية ذكية موثقة — المنصة جاهزة لاستقبال أي استفسارات دوائية ومراجعتها سريرياً."), cell_style)]
        ]
        t_drugs = Table(table_rows, colWidths=[535])
        t_drugs.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
            ('TOPPADDING', (0,0), (-1,-1), 8),
            ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ]))

    story.append(t_drugs)
    story.append(Spacer(1, 14))

    # 3. Disclaimer Footer
    footer_data = [
        [Paragraph(ar("⚠️ تنبيه رسمي: هذه الاستشارة مولدة بواسطة الذكاء الاصطناعي لمنصة AI-COS. يُرجى مراجعة الصيدلي أو الطبيب المختص قبل اتخاذ أي قرار علاجي."), sub_style)]
    ]
    t_foot = Table(footer_data, colWidths=[535])
    t_foot.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fff7ed')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#ea580c')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_foot)

    doc.build(story)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "attachment; filename=ai_cos_consultation_summary.pdf"
        }
    )
