"""
# مسؤوليته:
# تعريف الأخطاء المخصصة (Custom Exceptions) الخاصة بالتطبيق.
# يساعد في توحيد شكل الأخطاء المرجعة للمستخدم (مثل ValidationError أو NotFoundError).
#
# ممنوع أن يحتوي على:
# - الـ Exception Handlers التي تتعامل مع FastAPI مباشرة (الـ handlers تُسجل في main.py عادة).
"""
class NotFoundException(Exception):
    def __init__(self, item_name: str):
        self.item_name = item_name
        self.message = f"{item_name} not found"
        super().__init__(self.message)
