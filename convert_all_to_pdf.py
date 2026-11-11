import os
import re
import sys
import shutil
import subprocess
import fitz
import arabic_reshaper
from bidi.algorithm import get_display
from markdown_it import MarkdownIt

sys.stdout.reconfigure(encoding='utf-8')

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
FONT_PATH = r"C:\Windows\Fonts\tahoma.ttf"
LOCAL_MERMAID = r"D:/Graduation Project/mermaid.min.js"
SOURCE_DIR = r"D:\Graduation Project\صفحات 17"
OUTPUT_BUNDLE_DIR = os.path.join(SOURCE_DIR, "ملفات_PDF_جاهزة_للدكتور")

os.makedirs(OUTPUT_BUNDLE_DIR, exist_ok=True)

DOC_TITLES = {
    "صفحه استخبارات السوق والافعال التنفيذية.md": "استخبارات السوق والأفعال التنفيذية",
    "صفحه التحليلات والذكاء التجاري.md": "التحليلات ولوحة القيادة والذكاء التجاري",
    "صفحه التوريد ومشتريات.md": "المشتريات وسلاسل الإمداد ونظم الأعمال",
    "صفحه القيمة الاقتصادية للأعمال.md": "القيمة الاقتصادية للأعمال وعائد الاستثمار",
    "صفحه المحاسبه والتدقيق المالي.md": "المحاسبة والتدقيق المالي الجنائي",
    "صفحه بطاقه الاداء المتوازن.md": "بطاقة الأداء المتوازن والإدارة الاستراتيجية",
    "صفحه ذاكرة تصحيح الروشتات والتعلم المستمر.md": "ذاكرة تصحيح الروشتات والتعلم المستمر",
    "صفحه سجل المخاطر والحوكمة المؤسسية.md": "سجل المخاطر والحوكمة المؤسسية COSO",
    "صفحه سجلات التدقيق والتشفير الرقابي.md": "سجلات التدقيق والتشفير الرقابي WORM",
    "صفحه محاكي القرارات وماذا لو.md": "محاكي القرارات وحساسية التسعير وماذا لو",
    "صفحه مراجعه قرارات الذكاء الاصطناعي.md": "مراجعة قرارات الذكاء الاصطناعي HITL",
    "معمارية_واشكال_مشروع_MAJLIS_ERP.md": "معمارية ومخططات نظام MAJLIS AI-ERP",
    "هوية_وااسم_المشروع_MAJLIS_ERP.md": "هوية ورؤية مشروع MAJLIS AI-ERP"
}

CSS_STYLES = """
@page {
    size: A4;
    margin: 18mm 14mm 18mm 14mm;
}

* {
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-size: 13px;
    line-height: 1.8;
    color: #1e293b;
    background-color: #ffffff;
    direction: rtl;
    text-align: right;
    margin: 0;
    padding: 10px 14px;
}

/* Academic Header */
.academic-header {
    margin-bottom: 22px;
    page-break-after: avoid;
    break-after: avoid;
}

.academic-meta {
    display: flex;
    justify-content: space-between;
    align-items: center;
    direction: rtl;
    padding-bottom: 10px;
    border-bottom: 2px solid #2563eb;
}

.meta-right {
    display: flex;
    flex-direction: column;
    gap: 3px;
}

.univ-badge {
    font-size: 11px;
    font-weight: 700;
    color: #1e40af;
}

.proj-name {
    font-size: 13.5px;
    font-weight: 800;
    color: #0f172a;
}

.doc-badge {
    font-size: 10.5px;
    font-weight: 600;
    color: #475569;
    background: #f1f5f9;
    padding: 4px 10px;
    border-radius: 12px;
    border: 1px solid #cbd5e1;
    white-space: nowrap;
}

/* Headings */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif;
    font-weight: 700;
    color: #0f172a;
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    page-break-after: avoid;
    break-after: avoid;
    line-height: 1.4;
}

h1 {
    font-size: 21px;
    color: #1e3a8a;
    border-bottom: 2px solid #93c5fd;
    padding-bottom: 8px;
    margin-top: 0.6em;
}

h2 {
    font-size: 16px;
    color: #1e40af;
    border-right: 4px solid #3b82f6;
    padding-right: 10px;
    margin-top: 1.8em;
}

h3 {
    font-size: 14.5px;
    color: #0f172a;
}

h4 {
    font-size: 13.5px;
    color: #334155;
}

p {
    margin-top: 0.4em;
    margin-bottom: 0.8em;
    text-align: justify;
}

/* Blockquotes */
blockquote {
    background-color: #f8fafc;
    border-right: 4px solid #2563eb;
    border-left: none;
    margin: 1.2em 0;
    padding: 12px 18px;
    color: #1e293b;
    border-radius: 0 6px 6px 0;
    page-break-inside: avoid;
    break-inside: avoid;
}

blockquote p {
    margin: 0.3em 0;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    margin: 1.4em 0;
    font-size: 11.5px;
    page-break-inside: avoid;
    break-inside: avoid;
    direction: rtl;
}

th, td {
    border: 1px solid #cbd5e1;
    padding: 8px 12px;
    text-align: right;
    vertical-align: top;
}

th {
    background-color: #f1f5f9;
    color: #0f172a;
    font-weight: 700;
    border-bottom: 2px solid #94a3b8;
}

tr:nth-child(even) {
    background-color: #f8fafc;
}

/* Code Blocks & Inline Code */
code {
    font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
    font-size: 11px;
    background-color: #f1f5f9;
    color: #0f172a;
    border: 1px solid #e2e8f0;
    padding: 2px 6px;
    border-radius: 4px;
    direction: ltr;
    display: inline-block;
    unicode-bidi: isolate;
}

pre {
    background-color: #0f172a;
    color: #f8fafc;
    padding: 14px 18px;
    border-radius: 6px;
    overflow-x: auto;
    direction: ltr;
    text-align: left;
    margin: 1.2em 0;
    border: 1px solid #1e293b;
    page-break-inside: avoid;
    break-inside: avoid;
}

pre code {
    background-color: transparent;
    border: none;
    color: #f8fafc;
    padding: 0;
    font-size: 11px;
    line-height: 1.6;
    display: block;
}

/* Lists */
ul, ol {
    padding-right: 25px;
    padding-left: 0;
    margin: 0.6em 0;
}

li {
    margin-bottom: 0.4em;
    line-height: 1.7;
}

/* Horizontal Rule */
hr {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 1.6em 0;
}

/* Mermaid Diagrams */
.mermaid-container {
    text-align: center;
    margin: 1.8em auto;
    padding: 16px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    page-break-inside: avoid;
    break-inside: avoid;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.mermaid {
    display: inline-block;
    direction: ltr;
    margin: 0 auto;
}

.mermaid svg {
    max-width: 100% !important;
    height: auto !important;
    display: block;
    margin: 0 auto;
}

.mermaid text, .mermaid .nodeLabel, .mermaid span, .mermaid div {
    font-family: 'Segoe UI', Tahoma, Arial, sans-serif !important;
}

strong {
    color: #0f172a;
}

a {
    color: #2563eb;
    text-decoration: none;
    direction: ltr;
    unicode-bidi: isolate;
}
"""

def convert_md_to_html(md_path, title):
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_md = f.read()

    # Pre-process mermaid blocks
    mermaid_blocks = []
    def save_mermaid(match):
        idx = len(mermaid_blocks)
        content = match.group(1).strip()
        # Protect edge labels containing unquoted parentheses e.g. -->|نعم (Match Found)|
        content = re.sub(r'-->\|([^"|\n]*\([^"|\n]*\)[^"|\n]*)\|', r'-->|"\1"|', content)
        mermaid_blocks.append(content)
        return f"\n\n:::MERMAID_{idx}:::\n\n"

    processed_md = re.sub(r'```mermaid\s*\n(.*?)```', save_mermaid, raw_md, flags=re.DOTALL)

    md_parser = MarkdownIt('commonmark').enable('table').enable('strikethrough')
    body_html = md_parser.render(processed_md)

    # Restore mermaid blocks
    for idx, code in enumerate(mermaid_blocks):
        div_block = f'<div class="mermaid-container"><div class="mermaid">\n{code}\n</div></div>'
        body_html = body_html.replace(f'<p>:::MERMAID_{idx}:::</p>', div_block)
        body_html = body_html.replace(f':::MERMAID_{idx}:::', div_block)

    full_html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="file:///{LOCAL_MERMAID}"></script>
<style>
{CSS_STYLES}
</style>
</head>
<body>

<header class="academic-header">
  <div class="academic-meta">
    <div class="meta-right">
      <span class="univ-badge">جامعة بورسعيد · كلية تكنولوجيا الإدارة ونظم المعلومات (BIS / MBT)</span>
      <span class="proj-name">مشروع تخرج: MAJLIS AI · ERP — نظام تخطيط موارد المؤسسات بمجلس إدارة ذكي</span>
    </div>
    <div class="meta-left">
      <span class="doc-badge">وثيقة معمارية وهندسية</span>
    </div>
  </div>
</header>

{body_html}

<script>
mermaid.initialize({{
    startOnLoad: true,
    theme: 'neutral',
    securityLevel: 'loose',
    flowchart: {{
        htmlLabels: true,
        useMaxWidth: true
    }},
    sequence: {{
        useMaxWidth: true
    }},
    er: {{
        useMaxWidth: true
    }},
    state: {{
        useMaxWidth: true
    }}
}});
</script>
</body>
</html>"""
    return full_html

def stamp_pdf_footers(pdf_path, doc_title_ar):
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    font_file = FONT_PATH
    custom_font = fitz.Font(fontfile=font_file)

    for page_idx, page in enumerate(doc):
        rect = page.rect
        
        # Subtle footer divider line
        p1 = fitz.Point(36, rect.height - 30)
        p2 = fitz.Point(rect.width - 36, rect.height - 30)
        page.draw_line(p1, p2, color=(0.8, 0.85, 0.9), width=0.5)

        # Insert font
        font_name = "tahoma_footer"
        page.insert_font(fontname=font_name, fontfile=font_file)

        # Right-side text (Document Title in Arabic)
        right_raw = f"{doc_title_ar} · MAJLIS AI-ERP"
        bidi_right = get_display(arabic_reshaper.reshape(right_raw))
        tw_right = custom_font.text_length(bidi_right, fontsize=8)
        page.insert_text(
            fitz.Point(rect.width - 36 - tw_right, rect.height - 18),
            bidi_right,
            fontname=font_name,
            fontsize=8,
            color=(0.4, 0.45, 0.5)
        )

        # Left-side text (Page Number)
        page_raw = f"صفحة {page_idx + 1} من {total_pages}"
        bidi_page = get_display(arabic_reshaper.reshape(page_raw))
        page.insert_text(
            fitz.Point(36, rect.height - 18),
            bidi_page,
            fontname=font_name,
            fontsize=8,
            color=(0.4, 0.45, 0.5)
        )

    temp_stamped = pdf_path + ".tmp.pdf"
    doc.save(temp_stamped)
    doc.close()
    os.replace(temp_stamped, pdf_path)

def process_file(md_filename):
    md_path = os.path.join(SOURCE_DIR, md_filename)
    base_name = os.path.splitext(md_filename)[0]
    pdf_filename = base_name + ".pdf"
    dest_pdf_direct = os.path.join(SOURCE_DIR, pdf_filename)
    dest_pdf_bundle = os.path.join(OUTPUT_BUNDLE_DIR, pdf_filename)
    
    doc_title = DOC_TITLES.get(md_filename, base_name)
    print(f"\nProcessing [{md_filename}]...")
    
    html_content = convert_md_to_html(md_path, doc_title)
    temp_html = os.path.join(SOURCE_DIR, f"temp_{abs(hash(md_filename))}.html")
    with open(temp_html, 'w', encoding='utf-8') as f:
        f.write(html_content)

    temp_html_url = "file:///" + os.path.abspath(temp_html).replace("\\", "/")
    
    # Run Edge headless
    subprocess.run([
        EDGE_PATH,
        "--headless",
        "--disable-gpu",
        "--virtual-time-budget=12000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={dest_pdf_direct}",
        temp_html_url
    ], check=True, capture_output=True)

    if os.path.exists(temp_html):
        os.remove(temp_html)

    # Stamp footers
    stamp_pdf_footers(dest_pdf_direct, doc_title)
    
    # Copy to bundle folder
    shutil.copy2(dest_pdf_direct, dest_pdf_bundle)

    # Inspect final PDF
    doc = fitz.open(dest_pdf_direct)
    pages = len(doc)
    drawings = sum(len(p.get_drawings()) for p in doc)
    doc.close()
    size_kb = os.path.getsize(dest_pdf_direct) / 1024

    print(f"  ✓ SUCCESS: {pdf_filename} | {pages} pages | {drawings} vector elements | {size_kb:.1f} KB")
    return {
        "file": pdf_filename,
        "title": doc_title,
        "pages": pages,
        "drawings": drawings,
        "size_kb": size_kb
    }

def main():
    md_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith(".md")]
    md_files.sort()
    
    print(f"Starting conversion for {len(md_files)} markdown files in '{SOURCE_DIR}'...")
    results = []
    
    for f in md_files:
        res = process_file(f)
        results.append(res)
        
    print("\n" + "="*80)
    print("ALL FILES CONVERTED SUCCESSFULLY SUMMARY:")
    print("="*80)
    total_pages = 0
    total_size = 0
    for r in results:
        total_pages += r['pages']
        total_size += r['size_kb']
        print(f"• {r['file']:<50} | {r['pages']:>2} pages | {r['size_kb']:>6.1f} KB")
        
    print("-" * 80)
    print(f"Total PDFs generated: {len(results)}")
    print(f"Total pages: {total_pages}")
    print(f"Total size: {total_size / 1024:.2f} MB")
    print(f"Direct location: {SOURCE_DIR}")
    print(f"Bundle folder: {OUTPUT_BUNDLE_DIR}")
    print("="*80)

if __name__ == "__main__":
    main()
