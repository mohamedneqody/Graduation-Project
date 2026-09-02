"""
# مسؤوليته:
# يحتوي على منطق الأعمال الحقيقي (Business Logic).
# هنا يتم تنفيذ العمليات المطلوبة، الحسابات، واستدعاء عمليات قاعدة البيانات.
#
# ممنوع أن يحتوي على:
# - أي شيء يخص HTTP أو FastAPI (مثل Request, Response, HTTPException).
# - يجب أن يعتمد على الـ Dependencies المحقونة (مثل DB Session) وليس استيرادها مباشرة.
"""

async def get_all_products():
    # في التطبيق الحقيقي، سيتم استقبال db: AsyncSession كبارامتر
    # وإجراء الاستعلام، ثم إرجاع البيانات.
    return [{"id": 1, "name": "Test Product", "price": 100.0}]
