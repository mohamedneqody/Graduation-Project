# المعمارية الفنية: send_discount_offer Architecture

```mermaid
flowchart LR
    A[Webhook: POST /send_discount_offer] --> B[AI Marketing Agent: generate-campaign]
    B --> C[Ollama / Gemini: Personalized Copy & Coupon]
    C --> D[Telegram: Send Discount Offer to Patient]
```

## 📈 الأثر التجاري (Business Impact)
- **الحد من ترك الصيدلية (Churn Reduction):** استعادة ما يصل إلى 35% من المرضى المترددين في تجديد العلاج.
- **صياغة ذكية بالـ LLM:** صياغة إنسانية غير نمطية ترفع معدل التحويل (Conversion Rate).
