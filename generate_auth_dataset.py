import json
import random
import sys

SYSTEM_PROMPT = "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"

english_single_turn = [
    {
        "user": ["How do I register an account?", "how 2 register", "Can I make a new account?", "I want to sign up"],
        "assistant": "You can register for an AI-COS Pharmacy account using your email and a password, or by using Google OAuth for a quicker sign-up. If you choose the email option, please note that email verification is required."
    },
    {
        "user": ["I forgot my password", "pwd reset", "Help I cant login, forgot password", "How to change my password?"],
        "assistant": "To reset your password, click on the 'Forgot Password' link on the login page. We'll send you a secure password reset link via email. Note: If you registered using Google, you don't have a password with us and should simply click 'Sign in with Google'."
    },
    {
        "user": ["Delete my account now!", "I want to delete my data", "how to erase account"],
        "assistant": "I understand you want to manage your account. For security and audit purposes, we do not permanently delete accounts. Instead, we can deactivate your account. This ensures your medical and order history is preserved securely while removing your active presence. Let me know if you'd like to proceed with deactivation."
    },
    {
        "user": ["Can I browse without making an account?", "Do I need to sign up to see medicines?", "guest mode?"],
        "assistant": "Yes, absolutely! Guest browsing is fully supported. You can explore our catalog and read about our products without registering. However, to place an order or use our AI reminders, you will need to create an account."
    },
    {
        "user": ["What is a 404 error when I try to view a prescription?", "404 not found meaning"],
        "assistant": "A 404 error means the resource wasn't found or you don't have authorization to view it. For security reasons, we return a 404 (Not Found) instead of a 403 (Forbidden) for unauthorized access to protect user privacy. Please make sure you're logged into the correct account."
    },
    {
        "user": ["How do you store my password?", "is my data safe?"],
        "assistant": "Your security is our priority. We use Supabase Auth for our authentication. Your passwords are securely hashed, and our sessions use HttpOnly and Secure cookies. If you use Google OAuth, we don't store a password for you at all."
    },
    {
        "user": ["Can I change my preferred language?", "how to set arabic", "language settings"],
        "assistant": "Yes! You can update your customer profile to set your preferred_language to either Arabic or English. You can also update your preferred communication channel (WhatsApp, Email, or SMS)."
    }
]

arabic_single_turn = [
    {
        "user": ["كيف اسجل حساب؟", "تسجيل جديد", "ابغى اسوي حساب", "طريقة التسجيل"],
        "assistant": "يمكنك التسجيل في صيدلية AI-COS باستخدام بريدك الإلكتروني وكلمة المرور، أو باستخدام حساب Google لتسجيل أسرع. إذا اخترت البريد الإلكتروني، يرجى ملاحظة أنه سيطلب منك التحقق من بريدك الإلكتروني."
    },
    {
        "user": ["نسيت كلمة المرور", "كيف استرجع الباسورد", "نسيت الرمز"],
        "assistant": "لإعادة تعيين كلمة المرور، انقر على رابط 'نسيت كلمة المرور' في صفحة الدخول. سنرسل لك رابطاً عبر البريد الإلكتروني. ملاحظة: إذا سجلت باستخدام حساب Google، فلن تحتاج لكلمة مرور، فقط اختر 'تسجيل الدخول باستخدام Google'."
    },
    {
        "user": ["احذفوا حسابي فورا", "كيف الغي حسابي", "حذف الحساب"],
        "assistant": "أتفهم رغبتك في إدارة حسابك. لأسباب أمنية وللحفاظ على السجلات، نحن لا نقوم بحذف الحسابات نهائياً، بل نقوم بإلغاء تنشيطها. هذا يضمن حفظ سجلاتك الطبية بأمان. أخبرني إذا كنت ترغب في متابعة إلغاء التنشيط."
    },
    {
        "user": ["هل اقدر اتصفح بدون حساب؟", "تصفح كزائر", "لازم اسجل عشان اشوف الادوية؟"],
        "assistant": "نعم، بالتأكيد! يمكنك تصفح منتجاتنا كزائر بدون الحاجة لإنشاء حساب. ولكن لإتمام الطلب أو استخدام ميزة التذكير الذكي، ستحتاج إلى التسجيل."
    },
    {
        "user": ["أواجه خطأ 404", "يطلع لي صفحة غير موجودة"],
        "assistant": "خطأ 404 يعني أن الصفحة غير موجودة أو ليس لديك الصلاحية للوصول إليها. لأسباب أمنية ولحماية الخصوصية، نعرض خطأ 404 بدلاً من 403. يرجى التأكد من تسجيل الدخول بحسابك الصحيح."
    },
    {
        "user": ["هل بياناتي في أمان؟", "كيف تحفظون الباسورد"],
        "assistant": "أمانك هو أولويتنا. نستخدم نظام Supabase للمصادقة وتشفير كلمات المرور. وتستخدم جلساتنا ملفات تعريف ارتباط (Cookies) آمنة. وإذا استخدمت حساب Google، فنحن لا نخزن أي كلمة مرور لك."
    },
    {
        "user": ["كيف اغير اللغة", "اللغة العربية", "تغيير رقم الواتساب"],
        "assistant": "نعم! يمكنك تحديث ملفك الشخصي لاختيار لغتك المفضلة (العربية أو الإنجليزية). كما يمكنك تحديد قناة التواصل المفضلة لك مثل الواتساب، البريد الإلكتروني، أو الرسائل النصية."
    }
]

english_multi_turn = [
    [
        {"user": "I can't log in with my email.", "assistant": "I'm sorry to hear you're having trouble logging in. Did you originally sign up using your email and password, or did you use Google OAuth?"},
        {"user": "I think I used Google.", "assistant": "Great! If you used Google, your account doesn't have a password stored with us. Please go to the login page and click the 'Sign in with Google' button. Let me know if that works!"},
        {"user": "It worked, thanks!", "assistant": "You're very welcome! Let me know if you need help with anything else, like setting up medication reminders."}
    ],
    [
        {"user": "Why am I getting a 404 error on my prescription page?", "assistant": "A 404 error usually means the resource wasn't found, or you don't have authorization to view it. For privacy reasons, we return a 404 instead of a 'Forbidden' error. Are you sure you are logged into the correct account?"},
        {"user": "Oh, I might be logged out.", "assistant": "That would explain it! Please log back in. Your session uses secure, HttpOnly cookies, so you'll need to re-authenticate to view sensitive prescription details."}
    ]
]

arabic_multi_turn = [
    [
        {"user": "مو قادر ادخل حسابي", "assistant": "عذراً لمواجهة هذه المشكلة. هل سجلت حسابك باستخدام البريد الإلكتروني وكلمة المرور أم باستخدام حساب Google؟"},
        {"user": "اتوقع باستخدام جوجل", "assistant": "ممتاز! في هذه الحالة، حسابك لا يحتوي على كلمة مرور لدينا. يرجى التوجه لصفحة الدخول والنقر على 'تسجيل الدخول باستخدام Google'. جرب وأخبرني."},
        {"user": "ضبط، شكرا", "assistant": "العفو! أنا هنا دائماً لمساعدتك. هل تحتاج إلى مساعدة في أي شيء آخر؟"}
    ],
    [
        {"user": "ليش يطلع لي خطأ 404 لما افتح الوصفة الطبية؟", "assistant": "خطأ 404 يعني أن الصفحة غير موجودة أو أنه ليس لديك الصلاحية لفتحها. لحماية الخصوصية، نظهر 404 بدلاً من رسالة 'ممنوع'. هل أنت متأكد أنك سجلت الدخول؟"},
        {"user": "اه شكلي طلعت من الحساب", "assistant": "هذا يفسر الأمر! يرجى تسجيل الدخول مجدداً. نحن نستخدم ملفات ارتباط (Cookies) آمنة، لذا ستحتاج لتسجيل الدخول لرؤية معلوماتك الحساسة."}
    ]
]

def generate_samples():
    samples = []
    
    # Target 700 samples: 350 EN, 350 AR
    # We will generate a mix of single turn and multi-turn
    
    for _ in range(350):
        # English
        is_multi = random.random() < 0.3
        sample = {"messages": [{"role": "system", "content": SYSTEM_PROMPT}]}
        
        if is_multi:
            conv = random.choice(english_multi_turn)
            for turn in conv:
                sample["messages"].append({"role": "user", "content": turn["user"]})
                sample["messages"].append({"role": "assistant", "content": turn["assistant"]})
        else:
            qa = random.choice(english_single_turn)
            user_q = random.choice(qa["user"])
            # Add some typos randomly
            if random.random() < 0.1:
                user_q = user_q.lower().replace("account", "acount").replace("password", "pasword")
            sample["messages"].append({"role": "user", "content": user_q})
            sample["messages"].append({"role": "assistant", "content": qa["assistant"]})
            
        samples.append(sample)
        
    for _ in range(350):
        # Arabic
        is_multi = random.random() < 0.3
        sample = {"messages": [{"role": "system", "content": SYSTEM_PROMPT}]}
        
        if is_multi:
            conv = random.choice(arabic_multi_turn)
            for turn in conv:
                sample["messages"].append({"role": "user", "content": turn["user"]})
                sample["messages"].append({"role": "assistant", "content": turn["assistant"]})
        else:
            qa = random.choice(arabic_single_turn)
            user_q = random.choice(qa["user"])
            sample["messages"].append({"role": "user", "content": user_q})
            sample["messages"].append({"role": "assistant", "content": qa["assistant"]})
            
        samples.append(sample)
        
    # Shuffle the samples
    random.shuffle(samples)
    
    return samples

def main():
    samples = generate_samples()
    with open('D:/Graduation Project/dataset_batch_1_auth.jsonl', 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
            
if __name__ == "__main__":
    main()
