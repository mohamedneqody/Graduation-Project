"""
# مسؤوليته:
# تعريف الـ Dependencies (الحقن) المشتركة التي يتم استخدامها في عدة Routers.
# مثل: الحصول على الـ Current User، الـ Pagination Parameters، الخ.
#
# ممنوع أن يحتوي على:
# - Business logic خاص بـ Domain معين (هذا مكانه في services).
"""
from fastapi import Query

class PaginationParams:
    def __init__(self, page: int = Query(1), limit: int = Query(10)):
        self.page = page
        self.limit = limit
