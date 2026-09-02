import json
import random

system_prompt = "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"

topics_en = [
    ("I want to browse the catalog for chronic drugs.", "You can easily browse our catalog by selecting the 'Chronic' category. We have a wide range of medications available. Please consult your pharmacist or doctor for medical advice if you are unsure what to choose."),
    ("Can I order seasonal allergy meds?", "Yes, you can order seasonal medications directly through our platform. Just add them to your cart and proceed to checkout."),
    ("What happens if I order two drugs that interact poorly?", "Our system automatically checks for drug conflicts before you complete your order. If a potential interaction is detected, you will see a warning message and the case will be logged for review. Please consult your pharmacist or doctor for medical advice regarding any interactions."),
    ("Are there cross-sell recommendations?", "Yes! Based on your selections, we may recommend complementary products, such as suggesting Vitamin D when you purchase Calcium, or based on statistical co-purchasing patterns."),
    ("How can I track my order status?", "You can track your order status directly from your account dashboard. Every status transition is tracked in our system for full transparency."),
    ("Where do you get your prices?", "Our prices are securely calculated from our database base prices to ensure accuracy and fairness. We never rely on frontend price calculations."),
    ("Do you accept real credit cards right now?", "Currently, for our MVP, we are using a simulated payment integration. No real charges are processed."),
    ("How does shipping work?", "Shipping is simulated in our current MVP version. Once full operations begin, you will receive tracking details. Please note we are web-only right now."),
    ("Can I see acute drugs?", "Yes, you can filter our catalog to see 'Acute' medications. Please consult your pharmacist or doctor for medical advice before starting any new acute medication."),
    ("Can I buy prescription drugs?", "You can order prescription drugs, but valid verification may be required upon fulfillment. Please consult your pharmacist or doctor for medical advice."),
    ("What if a drug is out of stock?", "If a drug is out of stock, it will be marked as such in the catalog and cannot be added to your order."),
    ("Can I cancel my order?", "You can cancel your order before it reaches the processing stage. Please check your order status page for the cancellation option."),
    ("Tell me about ibuprofen.", "Ibuprofen is commonly used for pain relief and reducing inflammation. Please consult your pharmacist or doctor for medical advice."),
    ("Do I need to register to browse?", "No, guest browsing is completely allowed! You can view our entire catalog without registering."),
    ("Why can't a drug be deleted?", "If a drug has historical orders attached to it, it cannot be deleted to prevent business rule violations and maintain audit integrity."),
    ("Is there a mobile app?", "Currently, we are a web-only platform. You can access all our features seamlessly through your desktop or mobile browser.")
]

topics_ar = [
    ("أريد تصفح الأدوية المزمنة.", "يمكنك تصفح الكتالوج الخاص بنا بسهولة عن طريق تحديد فئة 'مزمن'. يرجى استشارة الصيدلي أو الطبيب للحصول على استشارة طبية."),
    ("هل يمكنني طلب أدوية الحساسية الموسمية؟", "نعم، يمكنك طلب الأدوية الموسمية مباشرة عبر منصتنا. فقط أضفها إلى عربة التسوق وتابع للدفع."),
    ("ماذا يحدث إذا طلبت دواءين يتعارضان؟", "يقوم نظامنا تلقائيًا بالتحقق من تعارض الأدوية قبل إكمال الطلب. إذا تم اكتشاف تعارض، سترى رسالة تحذير وسيتم تسجيل الحالة. يرجى استشارة الصيدلي أو الطبيب للحصول على استشارة طبية."),
    ("هل هناك توصيات لأدوية أخرى؟", "نعم! بناءً على اختياراتك، قد نوصي بمنتجات تكميلية، مثل اقتراح فيتامين د عند شراء الكالسيوم."),
    ("كيف أتتبع حالة طلبي؟", "يمكنك تتبع حالة طلبك مباشرة من لوحة التحكم في حسابك. يتم تتبع كل تغيير في الحالة لضمان الشفافية."),
    ("كيف تحسبون الأسعار؟", "يتم حساب الأسعار بشكل آمن من قاعدة بياناتنا لضمان الدقة. لا نقبل حسابات الأسعار من واجهة المستخدم."),
    ("هل تقبلون بطاقات الائتمان الحقيقية؟", "حاليًا في نسختنا التجريبية، نستخدم نظام دفع محاكى. لا تتم معالجة مدفوعات حقيقية."),
    ("كيف يتم الشحن؟", "الشحن محاكى حاليًا في نسختنا التجريبية. نحن نعمل كمنصة ويب فقط في الوقت الحالي."),
    ("هل يمكنني رؤية الأدوية الحادة؟", "نعم، يمكنك تصفية الكتالوج لرؤية الأدوية الحادة. يرجى استشارة الصيدلي أو الطبيب للحصول على استشارة طبية."),
    ("ماذا عن الأدوية الوصفية؟", "يمكنك طلب الأدوية التي تحتاج لوصفة، ولكن قد يُطلب التحقق منها. يرجى استشارة الصيدلي أو الطبيب للحصول على استشارة طبية."),
    ("ماذا لو كان الدواء غير متوفر؟", "إذا كان الدواء غير متوفر، سيظهر ذلك في الكتالوج ولن تتمكن من إضافته للطلب."),
    ("هل يمكنني إلغاء الطلب؟", "يمكنك إلغاء الطلب قبل أن يصل إلى مرحلة التجهيز من خلال صفحة حالة الطلب."),
    ("ما هي استخدامات الباراسيتامول؟", "الباراسيتامول يستخدم لتسكين الألم وخفض الحرارة. يرجى استشارة الصيدلي أو الطبيب للحصول على استشارة طبية."),
    ("هل يجب التسجيل للتصفح؟", "لا، يُسمح بتصفح الزوار! يمكنك رؤية كل الكتالوج دون تسجيل."),
    ("لماذا لا يمكن حذف دواء؟", "إذا كان الدواء مرتبطًا بطلبات سابقة، لا يمكن حذفه للحفاظ على سلامة قواعد العمل وسجلات التدقيق."),
    ("هل يوجد تطبيق للهاتف؟", "نحن منصة ويب فقط في الوقت الحالي، لكن يمكنك الوصول لكل الميزات عبر متصفح الهاتف.")
]

personas = [
    ("Beginner:", "Friendly and simple"),
    ("Angry:", "Frustrated and demanding"),
    ("Confused:", "Unsure and asking for clarification"),
    ("Technical:", "Detail-oriented and specific")
]

samples = []
for i in range(700):
    is_ar = random.choice([True, False])
    source = topics_ar if is_ar else topics_en
    q, a = random.choice(source)
    
    mutation = random.randint(1, 4)
    if mutation == 1:
        q = q + (" Please help." if not is_ar else " الرجاء المساعدة.")
    elif mutation == 2:
        q = ("Uh, " if not is_ar else "امم، ") + q.lower()
    elif mutation == 3:
        q = q.replace("?", "??").replace(".", "...")
    
    persona = random.choice(personas)
    if persona[0] == "Angry:":
        q = q.upper() + (" RIGHT NOW!" if not is_ar else " الآن!")
    elif persona[0] == "Confused:":
        q = q + (" I am very confused..." if not is_ar else " أنا مرتبك جدًا...")
        
    sample = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": q},
            {"role": "assistant", "content": a}
        ]
    }
    samples.append(json.dumps(sample, ensure_ascii=False))

with open('D:/Graduation Project/dataset_batch_2_drugs_orders.jsonl', 'w', encoding='utf-8') as f:
    for s in samples:
        f.write(s + '\n')
print(f'Generated {len(samples)} samples.')
