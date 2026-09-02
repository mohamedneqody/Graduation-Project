"""
# مسؤوليته:
# إعداد نظام تسجيل الأحداث (Logging) للتطبيق بالكامل.
# يضمن أن جميع الرسائل في التطبيق تتبع تنسيقًا موحدًا (وقت + مستوى الخطورة + الرسالة).
#
# ممنوع أن يحتوي على:
# - استدعاءات فعلية للـ logger لإخراج رسائل متعلقة بسير العمل (هذا الملف للـ Configuration فقط).
"""
import logging
import sys

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
