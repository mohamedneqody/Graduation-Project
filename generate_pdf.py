import os
import sys
import arabic_reshaper
from bidi.algorithm import get_display

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def ar(text):
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)

# Register Arabic Fonts
pdfmetrics.registerFont(TTFont('Arabic', 'C:/Windows/Fonts/arial.ttf'))
pdfmetrics.registerFont(TTFont('Arabic-Bold', 'C:/Windows/Fonts/arialbd.ttf'))

pdf_path = "D:/Graduation Project/بيرت/دليل_برومتات_الفيديو.pdf"
doc = SimpleDocTemplate(
    pdf_path,
    pagesize=A4,
    rightMargin=25,
    leftMargin=25,
    topMargin=20,
    bottomMargin=20
)

story = []

# Styles
title_style = ParagraphStyle(
    'ArabicTitle',
    fontName='Arabic-Bold',
    fontSize=15,
    leading=20,
    alignment=1, # Center
    textColor=colors.HexColor('#0f766e')
)

subtitle_style = ParagraphStyle(
    'ArabicSubtitle',
    fontName='Arabic',
    fontSize=10,
    leading=14,
    alignment=1,
    textColor=colors.HexColor('#334155')
)

badge_style = ParagraphStyle(
    'ArabicBadge',
    fontName='Arabic-Bold',
    fontSize=10,
    leading=13,
    alignment=2, # Right
    textColor=colors.HexColor('#0284c7')
)

prompt_style = ParagraphStyle(
    'ArabicPrompt',
    fontName='Arabic-Bold',
    fontSize=10,
    leading=14,
    alignment=2, # Right
    textColor=colors.HexColor('#0f172a')
)

goal_style = ParagraphStyle(
    'ArabicGoal',
    fontName='Arabic',
    fontSize=8.5,
    leading=11,
    alignment=2, # Right
    textColor=colors.HexColor('#64748b')
)

# Header Table
header_data = [
    [Paragraph(ar("🎬 دليل برومتات استعراض وتصوير مشروع التخرج — منصة AI-COS 2026"), title_style)],
    [Paragraph(ar("جامعة بورسعيد — كلية تكنولوجيا الإدارة ونظم المعلومات — قسم نظم المعلومات الإدارية (BIS / MTIS)"), subtitle_style)],
    [Paragraph(ar("مطور الذكاء الاصطناعي: محمد ياسر سعد نقودي │ فريق العمل: يوسف نوفل، زياد جودة، محمود طنطاوي، حسن حسين مخلص، مصطفى هاشم"), subtitle_style)],
]
header_table = Table(header_data, colWidths=[545])
header_table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdfa')),
    ('BOX', (0,0), (-1,-1), 1.5, colors.HexColor('#0f766e')),
    ('ROUNDEDCORNERS', [6, 6, 6, 6]),
    ('TOPPADDING', (0,0), (-1,-1), 6),
    ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
]))

story.append(header_table)
story.append(Spacer(1, 8))

prompts = [
    ("برومت 1: إثبات الهوية والجامعة والقسم", "من أنت، وما هي جامعتك وكليتك وقسمك، ومن هو مطور الذكاء الاصطناعي الذي قام ببنائك؟", "الهدف: إثبات ملكية المشروع وهوية الكلية وقسم BIS ومطور النموذج."),
    ("برومت 2: استعراض جميع أعضاء فريق العمل المساعد", "من هم جميع أعضاء فريق العمل المساعد الذين شاركوا في تطوير منصة AI-COS؟", "الهدف: إظهار ظهور جميع أعضاء الفريق الخمسة المساعدين بشكل رسمي."),
    ("برومت 3: استعلام لحظي عن سعر دواء في DB", "هل دواء alerid 10 mg متوفر وما هو سعره الرسمي في كتالوج الصيدلية؟", "الهدف: إثبات اتصال الـ RAG بقاعدة البيانات واستخراج السعر الحقيقي 63.00 ج.م."),
    ("برومت 4: الذاكرة الحوارية وتذكر اسم المستخدم", "أنا اسمي محمد وانت .. ما هو اسمي؟", "الهدف: إبراز الذاكرة الحوارية (Stateful Memory) وتذكر هوية واسم العميل."),
    ("برومت 5: حل الضمائر التتابعية (Coreference Resolution)", "هل متوفر septazole forte 800/160mg 10 tabs؟ ثم: طب كم سعره؟", "الهدف: إظهار فهم الضمائر التتابعية وربط السؤال الثاني بالدواء المذكور أولاً."),
    ("برومت 6: فهم المصطلحات العامية والشعبية المصرية", "عندي سخونية ورشح جامد ايه العلاج المناسب؟", "الهدف: إبراز المعالجة المسبقة للهجات وترجمة العامية لتصنيفات طبية رسمية."),
    ("برومت 7: المساعد الحسابي الحتمي الدقيق 100%", "احسبلي سعر 3 علب من دواء alerid 10 mg مع كود الخصم CARE15", "الهدف: إبراز المحرك الحسابي الحتمي (منع هلوسة الأسعار وحساب الخصم والكمية بدقة)."),
    ("برومت 8: دليل الحساب والعروض والكوبونات", "ازاي اعمل حساب جديد وازاي اخد خصم؟", "الهدف: إبراز معرفة البوت بطرق التسجيل (Google OAuth) وكود الخصم CARE15."),
    ("برومت 9: نظام التذكير الذكي ولوحة التحليلات", "كيف يساعد نظام التذكير الذكي (Refill Reminder) مرضى الأمراض المزمنة؟", "الهدف: شرح الخوارزمية التنبؤية لحساب دورات استهلاك الأدوية."),
    ("برومت 10: صمام الأمان الطبي والتصعيد للطوارئ", "المريض بلع شريط كامل وعنده ضيق تنفس حاد", "الهدف: إظهار كشف الطوارئ الفوري والتحذير الطبي الأحمر للتصعيد العاجل."),
]

for title, prompt_text, goal in prompts:
    card_data = [
        [Paragraph(ar(title), badge_style)],
        [Paragraph(ar(prompt_text), prompt_style)],
        [Paragraph(ar(goal), goal_style)],
    ]
    card_table = Table(card_data, colWidths=[545])
    card_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#ffffff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('LINEAFTER', (0,0), (0,-1), 4, colors.HexColor('#0284c7')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(card_table)
    story.append(Spacer(1, 4))

doc.build(story)
print("PDF successfully updated!")
