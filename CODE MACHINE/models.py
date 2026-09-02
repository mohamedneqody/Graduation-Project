import joblib
import pandas as pd

# 1. تحديد مسار النموذج
model_path = r"D:\Graduation Project\backend\backend\models\regression_xgboost.joblib"

# 2. تحميل النموذج
model = joblib.load(model_path)
print("تم تحميل النموذج بنجاح!")

# 3. إعداد بيانات عميل جديد (بالأسماء الصحيحة التي يتوقعها النموذج)
sample_data = pd.DataFrame([{
    'avg_cycle_days': 30.5,             # متوسط أيام دورة الشراء السابقة
    'days_since_last_purchase': 28,     # عدد الأيام منذ آخر عملية شراء
    'total_purchases_count': 5,         # إجمالي عدد مرات الشراء السابقة
    'cycle_std_days': 2.1,              # الانحراف المعياري لأيام الدورة (مدى انتظام العميل)
    'customer_age_group': '30-45',      # الفئة العمرية للعميل (نص)
    'drug_category': 'القلب والضغط',       # الفئة الطبية للدواء (نص)
    'drug_default_cycle_days': 30.0,    # الدورة الافتراضية للدواء
    'drug_base_price': 150.0            # السعر
}])

# 4. التوقع
# الـ Pipeline سيقوم تلقائياً بتحويل النصوص (age_group و drug_category) لأرقام
prediction = model.predict(sample_data)
print(f"أيام الدورة المتوقعة لهذا العميل هي: {prediction[0]:.2f} يوم")