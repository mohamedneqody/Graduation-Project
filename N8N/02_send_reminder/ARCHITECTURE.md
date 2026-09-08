# المعمارية الفنية: send_reminder Architecture

```mermaid
flowchart TD
    A[Trigger: Webhook /send_reminder] --> B[FastAPI: /internal/governance/pending]
    B --> C{Decision == auto_send?}
    C -- Yes --> D[Telegram: Send Patient Reminder]
    D --> E[FastAPI: PATCH /status=sent]
    C -- No --> F[Telegram: Alert Pharmacist - Human Review]
```

## 📊 تدفق البيانات (Data Payload)
- **Customer Name & Drug Name:** تُعرض في الرسالة الموجهة للمريض بصيغة HTML مريحة للعين.
- **Audit Tracking:** بمجرد نجاح الإرسال، يُطلق استدعاء PATCH لتوثيق وقت الإرسال وحالة السجل.
