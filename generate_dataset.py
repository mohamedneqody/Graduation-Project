import json
import random
import os

system_prompt = "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"

topics = [
    'reminder_system', 'why_reminder', 'timing', 'unsubscribe', 'governance',
    'human_review', 'shap', 'churn', 'rag', 'drug_info', 'accuracy', 'ab_testing',
    'marketing', 'coupons', 'cold_start', 'prediction_accuracy', 'models', 'privacy'
]

en_templates = {
    'reminder_system': [
        ("How does the automatic refill reminder work?", "Our AI Refill Reminder System calculates your average purchase cycle (the average days between your purchases of the same item). It schedules a reminder when you reach 85% of that cycle. For instance, if you buy something every 30 days, we'll remind you on day 25 so you don't run out!"),
        ("What is this AI reminder thing?", "The AI reminder is a smart feature that predicts when you might run out of your medication based on your past orders. It sends you a timely notification (usually via WhatsApp or Email) to reorder before you run out. Please remember, for any medical advice questions, always consult your pharmacist or doctor.")
    ],
    'why_reminder': [
        ("Why did I get a message to buy {drug} today?", "You received this reminder because our system noticed you usually order {drug} around this time in your cycle. We calculated that you might be running low soon. Please consult your pharmacist or doctor for medical advice if your dosage has changed."),
        ("I got an alert about my medication. Why?", "Our smart system tracks your order history and calculates an average cycle. When you're about 85% through that cycle, it sends a friendly reminder so you never run out of your essentials. Please consult your pharmacist or doctor for medical advice if needed.")
    ],
    'unsubscribe': [
        ("Stop sending me these reminders! How do I turn them off?", "I apologize if the reminders are bothersome. You can easily opt out by replying 'STOP' to the message or by visiting your account settings on our platform and toggling off 'AI Reminders'. Let me know if you need help with that."),
        ("I don't want AI reminders anymore.", "No problem at all! You can unsubscribe by going to your dashboard settings and disabling the 'Refill Reminders' option. You will no longer receive these automated messages.")
    ],
    'drug_info': [
        ("Can I take {drug1} with {drug2}?", "I can provide general information from our database, but I cannot give specific clinical recommendations. Please consult your pharmacist or doctor for medical advice regarding drug interactions between {drug1} and {drug2}."),
        ("What are the side effects of {drug}?", "Common side effects listed for {drug} include drowsiness and nausea, according to our RAG knowledge base. However, this is for informational purposes only. Please consult your pharmacist or doctor for medical advice.")
    ],
    'ab_testing': [
        ("As a store owner, how does the A/B testing work for reminders?", "Our Marketing Agent splits your eligible customers into two groups (50/50). One group receives a personalized reminder with a discount code (like CARE15), while the other gets a standard reminder. You can track which strategy drives better conversions in your Analytics Dashboard."),
        ("What's the point of the A/B testing feature?", "It helps you optimize your marketing! By testing a message with a coupon against one without, you can see if the discount actually improves reorder rates or if customers reorder anyway. The results are updated in real-time on your dashboard.")
    ],
    'shap': [
        ("What is SHAP in the analytics dashboard?", "SHAP (SHapley Additive exPlanations) is a tool we use for explainability. It shows exactly why our AI model made a specific prediction, such as predicting a customer's churn risk, by highlighting which features (like browsing frequency or days since last purchase) impacted the decision the most.")
    ],
    'governance': [
        ("How do you decide when to send an automated reminder versus checking manually?", "We use a Governance Engine (FR-07). If the AI is over 80% confident, the reminder is sent automatically. If confidence is between 50% and 80%, the system flags it for Human Review by pharmacy staff. Below 50%, no action is taken.")
    ],
    'human_review': [
        ("Why is my reminder pending human review?", "Sometimes our AI needs a second opinion! If the prediction confidence is between 50% and 80%, or if there's a high churn risk detected, the system routes the reminder to our pharmacy staff for a manual check before sending it out. This ensures accuracy.")
    ],
    'churn': [
        ("How does the churn risk alert work?", "Our Churn Prediction model analyzes customer behavior (like RFM metrics) to predict if a customer might stop buying. If the churn probability is over 70%, it forces a human review for their reminders, allowing staff to potentially intervene with a special offer.")
    ],
    'rag': [
        ("How does your chatbot know so much?", "Our RAG (Retrieval-Augmented Generation) chatbot uses a vector database (pgvector) to search our extensive knowledge base of drug info and store policies. It then uses an advanced language model to formulate a helpful response. Please consult your pharmacist or doctor for medical advice, though!")
    ],
    'cold_start': [
        ("I'm a new customer, how do reminders work for me?", "Welcome! For new customers, we face a 'cold-start' problem since we don't know your habits yet. We use a default cycle based on the drug category. Once you make 2-3 purchases, the AI will learn your personal cycle and adjust the reminders!")
    ],
    'privacy': [
        ("Are you using my personal data for AI?", "We take privacy seriously. Our Feature Store only uses generalized metrics like 'days since last purchase' or 'category type' rather than specific drug names when training models. Your sensitive health data is protected.")
    ]
}

ar_templates = {
    'reminder_system': [
        ("كيف يعمل نظام التذكير التلقائي؟", "يقوم نظام التذكير الذكي لدينا بحساب متوسط دورة الشراء الخاصة بك. ويقوم بجدولة تذكير عندما تصل إلى 85٪ من تلك الدورة. على سبيل المثال، إذا كنت تشتري دواء كل 30 يومًا، فسنذكرك في اليوم 25!"),
        ("ما هو التذكير بالذكاء الاصطناعي؟", "التذكير بالذكاء الاصطناعي هو ميزة ذكية تتوقع متى قد ينفد دواؤك بناءً على طلباتك السابقة. يرسل لك إشعارًا (عادةً عبر واتساب أو البريد الإلكتروني). يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية.")
    ],
    'why_reminder': [
        ("لماذا وصلتني رسالة لشراء {drug} اليوم؟", "لقد تلقيت هذا التذكير لأن نظامنا لاحظ أنك تطلب {drug} عادةً في هذا الوقت. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية إذا تغيرت جرعتك."),
        ("وصلني تنبيه بخصوص دوائي. لماذا؟", "يتتبع نظامنا الذكي سجل طلباتك. عندما تقترب من نهاية دوائك (حوالي 85٪ من المدة المعتادة)، يرسل تذكيرًا وديًا. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية.")
    ],
    'unsubscribe': [
        ("توقفوا عن إرسال هذه التذكيرات! كيف يمكنني إيقافها؟", "أعتذر إذا كانت التذكيرات مزعجة. يمكنك إيقافها بسهولة عن طريق الرد بكلمة 'STOP' أو من خلال إعدادات حسابك على منصتنا بتعطيل 'تذكيرات الذكاء الاصطناعي'."),
        ("لا أريد تذكيرات الذكاء الاصطناعي بعد الآن.", "لا مشكلة على الإطلاق! يمكنك إلغاء الاشتراك بالانتقال إلى إعدادات لوحة التحكم وتعطيل خيار التذكيرات.")
    ],
    'drug_info': [
        ("هل يمكنني تناول {drug1} مع {drug2}؟", "يمكنني تقديم معلومات عامة من قاعدة بياناتنا، ولكن لا يمكنني تقديم توصيات سريرية. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية بخصوص التفاعلات الدوائية."),
        ("ما هي الآثار الجانبية لدواء {drug}؟", "الآثار الجانبية الشائعة المدرجة تشمل النعاس والغثيان، وفقًا لقاعدة معارفنا. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية.")
    ],
    'governance': [
        ("كيف تقررون متى يتم إرسال التذكير تلقائيًا؟", "نستخدم محرك حوكمة. إذا كانت ثقة الذكاء الاصطناعي أعلى من 80٪، يتم إرسال التذكير تلقائيًا. إذا كانت الثقة بين 50٪ و 80٪، يتم تحويله للمراجعة البشرية من قبل طاقم الصيدلية. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية.")
    ],
    'rag': [
        ("كيف يعرف الروبوت كل هذه المعلومات؟", "يستخدم الروبوت الخاص بنا تقنية RAG للبحث في قاعدة معارفنا الشاملة. يُرجى استشارة الصيدلي أو الطبيب المختص للحصول على استشارة طبية!")
    ],
    'cold_start': [
        ("أنا عميل جديد، كيف تعمل التذكيرات معي؟", "مرحبًا بك! للعملاء الجدد، نستخدم دورة افتراضية بناءً على فئة الدواء. بمجرد قيامك بـ 2-3 عمليات شراء، سيتعلم الذكاء الاصطناعي دورتك الشخصية!")
    ],
    'privacy': [
        ("هل تستخدمون بياناتي الشخصية في الذكاء الاصطناعي؟", "نحن نأخذ الخصوصية على محمل الجد. نستخدم مقاييس عامة مثل 'أيام منذ آخر شراء' أو 'نوع الفئة' بدلاً من أسماء الأدوية المحددة عند تدريب النماذج.")
    ]
}

drugs = ['Panadol', 'Aspirin', 'Lipitor', 'Metformin', 'Amoxicillin', 'Omeprazole', 'Lisinopril', 'Levothyroxine', 'Ibuprofen', 'Zyrtec', 'Crestor', 'Nexium', 'Ventolin', 'Plavix', 'Synthroid']

samples = []

# Generate 800 samples
for i in range(800):
    lang = random.choice(['en', 'ar'])
    if lang == 'en':
        cat = random.choice(list(en_templates.keys()))
        q, a = random.choice(en_templates[cat])
    else:
        cat = random.choice(list(ar_templates.keys()))
        q, a = random.choice(ar_templates[cat])
        
    drug1 = random.choice(drugs)
    drug2 = random.choice([d for d in drugs if d != drug1])
    
    q = q.replace('{drug}', drug1).replace('{drug1}', drug1).replace('{drug2}', drug2)
    a = a.replace('{drug}', drug1).replace('{drug1}', drug1).replace('{drug2}', drug2)
    
    # Add some variability
    if random.random() < 0.3:
        q = q.lower()
    
    samples.append({
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    })

os.makedirs('d:/Graduation Project', exist_ok=True)
with open('d:/Graduation Project/dataset_batch_3_ai_features.jsonl', 'w', encoding='utf-8') as f:
    for s in samples:
        f.write(json.dumps(s, ensure_ascii=False) + '\n')
