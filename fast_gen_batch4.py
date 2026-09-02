import json
import random

SYSTEM_PROMPT = "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"

templates_en = [
    ("How do I read the Repeat Purchase Rate on the dashboard?", "The Repeat Purchase Rate shows the percentage of customers who have bought the same drug more than once. You can find it on the main dashboard under 'Customer Retention'."),
    ("What does the Churn Rate mean?", "The Churn Rate represents the percentage of customers who exceeded their average cycle days by 1.5 times without repurchasing. It helps identify customers at risk of stopping their treatment."),
    ("Can you explain the A/B Test Conversion Delta?", "Certainly! The A/B Test Conversion Delta shows the difference in conversion rates between the message sent with a discount and the message sent without a discount. This helps evaluate the effectiveness of the coupon."),
    ("Where can I find the Executive Copilot weekly reports?", "The Executive Copilot automatically sends a weekly summary to your WhatsApp. You can also view past summaries in the 'Reports' section of the dashboard."),
    ("What is Prediction MAE?", "Prediction MAE stands for Mean Absolute Error. It measures the average error in days between our AI's predicted refill date and the actual refill date. Our target is to keep this under 3 days."),
    ("How is the analytics dashboard updated? Is it real-time?", "Yes, the dashboard features real-time KPI updates using WebSockets/SSE. It is separated from the operational database (OLTP) to prevent any slowdowns while providing live data."),
    ("What is the Cross-sell Attach Rate target?", "Our target for the Cross-sell Attach Rate is ≥8%. This KPI measures the percentage of orders that include an additionally recommended complementary or market-basket product."),
    ("How do I interpret the SHAP explanations?", "SHAP explanations on the dashboard show you *why* the AI made a specific prediction (like a high churn risk). It highlights which factors (e.g., days since last purchase, average cycle) contributed most to the decision."),
    ("Is customer data private in the analytics?", "Yes, privacy is a priority. The Feature Store uses general categories (e.g., chronic-blood pressure) rather than specific drug names for analytics. Specific drug names are restricted to operational tables with strict access controls."),
    ("My dashboard isn't loading the latest KPIs.", "Please ensure you have a stable internet connection as the dashboard relies on live WebSockets. If the issue persists, try refreshing the page or checking if the n8n KPI Aggregation workflow (Workflow 4) ran successfully today.")
]

templates_ar = [
    ("كيف أقرأ معدل تكرار الشراء في لوحة التحكم؟", "معدل تكرار الشراء (Repeat Purchase Rate) يوضح النسبة المئوية للعملاء الذين اشتروا نفس الدواء أكثر من مرة. يمكنك العثور عليه في لوحة التحكم الرئيسية تحت قسم 'الاحتفاظ بالعملاء'."),
    ("ماذا يعني معدل التهرب (Churn Rate)؟", "معدل التهرب يمثل نسبة العملاء الذين تجاوزوا متوسط دورة الشراء الخاصة بهم بمقدار 1.5 مرة دون إعادة الشراء. هذا المؤشر يساعد في تحديد العملاء المعرضين لخطر التوقف عن العلاج."),
    ("هل يمكنك شرح A/B Test Conversion Delta؟", "بالتأكيد! يوضح هذا المؤشر الفرق في معدلات التحويل بين الرسائل التذكيرية التي تحتوي على خصم وتلك التي لا تحتوي على خصم، مما يساعد في تقييم فعالية حملات التسويق."),
    ("أين يمكنني العثور على تقارير Executive Copilot الأسبوعية؟", "يقوم Executive Copilot بإرسال ملخص أسبوعي تلقائياً عبر واتساب الخاص بصاحب الصيدلية. يمكنك أيضاً عرض الملخصات السابقة في قسم 'التقارير' في لوحة التحكم."),
    ("ما هو Prediction MAE؟", "يشير Prediction MAE إلى متوسط الخطأ المطلق في توقعات الذكاء الاصطناعي. وهو يقيس متوسط الخطأ (بالأيام) بين تاريخ إعادة التعبئة المتوقع والتاريخ الفعلي. هدفنا هو إبقاء هذا الخطأ أقل من 3 أيام."),
    ("هل يتم تحديث لوحة التحكم في الوقت الفعلي؟", "نعم، توفر لوحة التحكم تحديثات حية للمؤشرات باستخدام تقنية WebSockets/SSE. وهي مفصولة عن قاعدة البيانات التشغيلية لضمان عدم حدوث أي بطء في النظام الأساسي."),
    ("ما هو الهدف لمعدل البيع المتقاطع (Cross-sell Attach Rate)؟", "هدفنا لمعدل البيع المتقاطع هو ≥8%. يقيس هذا المؤشر نسبة الطلبات التي تتضمن منتجاً إضافياً موصى به (مثل المكملات الغذائية المرتبطة بالدواء الأساسي)."),
    ("كيف أقرأ تفسيرات SHAP في لوحة التحكم؟", "توضح تفسيرات SHAP في لوحة التحكم *السبب* وراء اتخاذ الذكاء الاصطناعي لقرار معين (مثل ارتفاع خطر التهرب). حيث تبرز العوامل الأكثر تأثيراً في القرار مثل 'عدد الأيام منذ آخر شراء'."),
    ("هل بيانات العملاء محمية في قسم التحليلات؟", "نعم، الخصوصية أولوية. يستخدم النظام الفئات العامة للأدوية (مثل أمراض مزمنة-ضغط الدم) في التحليلات بدلاً من أسماء الأدوية الدقيقة، والتي تقتصر على الجداول التشغيلية بصلاحيات وصول صارمة."),
    ("لوحة التحكم لا تعرض أحدث المؤشرات.", "يرجى التأكد من استقرار اتصالك بالإنترنت لأن لوحة التحكم تعتمد على اتصال حي (WebSockets). إذا استمرت المشكلة، جرب تحديث الصفحة أو تأكد من عمل مسار تجميع المؤشرات (Workflow 4) في n8n بشكل صحيح.")
]

def add_noise(text):
    if random.random() < 0.2:
        text = text.replace("dashboard", "dashbord").replace("لوحة التحكم", "لوحه التحكم")
    if random.random() < 0.2:
        text = text.replace("?", " ??").replace("؟", " ؟؟")
    return text

generated = []
for i in range(700):
    if i % 2 == 0:
        q, a = random.choice(templates_ar)
    else:
        q, a = random.choice(templates_en)
        
    q = add_noise(q)
    
    # Sometimes add a follow up
    if random.random() < 0.3:
        if i % 2 == 0:
            q2, a2 = random.choice(templates_ar)
        else:
            q2, a2 = random.choice(templates_en)
            
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
            {"role": "user", "content": q2},
            {"role": "assistant", "content": a2}
        ]
    else:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
        
    generated.append({"messages": messages})

with open("D:/Graduation Project/dataset_batch_4_dashboard.jsonl", "w", encoding="utf-8") as f:
    for item in generated:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")
