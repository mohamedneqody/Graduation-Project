# المعمارية الفنية: weekly_summary Architecture

```mermaid
flowchart LR
    A[Schedule: Mondays 8 AM] --> C[FastAPI: /api/v1/business-value/roi]
    B[Webhook: POST /weekly_summary] --> C
    C --> D[Business Value Engine: Calculate Savings & DDI Stats]
    D --> E[Telegram Bot: Send Executive Digest to Board]
```

## 💼 قيمة نظم معلومات الأعمال (BIS Value)
- **دعم اتخاذ القرار (Decision Support):** يمنح الإدارة العليا رؤية فورية للأثر المالي للأخطاء الطبية التي تم تجنبها.
- **تقارير بدون تدخل بشري (Automated Reporting):** أتمتة جمع البيانات من قاعدة البيانات وإرسالها لصناع القرار.
