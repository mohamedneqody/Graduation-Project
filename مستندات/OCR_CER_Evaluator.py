# -*- coding: utf-8 -*-
"""
OCR CER Evaluator — قياس دقة محرك قراءة الروشتات (AI-COS Pharmacy)
====================================================================
يحسب Character Error Rate (CER) و Word Error Rate (WER) لمخرجات محرك الـ OCR
مقارنةً بنص حقيقي موصوف يدوياً (Ground Truth)، مقسّمة حسب نوع الخط
(مطبوع / يدوي) — لإنتاج جدول الأرقام الجاهز للجنة المناقشة.

الاستخدام:
  1) جهّز مجلد صور الروشتات التجريبية (30–50 صورة كافية)
  2) جهّز ملف CSV بالأعمدة: image_file,expected_text,line_type
       line_type إما: printed أو handwritten
       مثال سطر: rx_001.jpg,"Augmentin 1g tablets",handwritten
  3) شغّل:
       python OCR_CER_Evaluator.py --images ./eval_images --truth ground_truth.csv \
            --endpoint http://127.0.0.1:9202/analyze
  4) النتيجة: ملف ocr_eval_results.md + جدول في الكونسول — جاهز للعرض.

ملاحظة: عدّل OCR_RESPONSE_KEYS إذا كان شكل استجابة سيرفر الـ 9202 مختلفاً.
"""
import argparse
import csv
import json
import os
import re
import sys
import urllib.request
import urllib.error

# مفاتيح متوقعة في رد سيرفر OCR — تُجرَّب بالترتيب حتى يُعثر على نصوص السطور
OCR_RESPONSE_KEYS = ["lines", "ocr_lines", "text_lines", "texts", "results"]


def levenshtein(a: str, b: str) -> int:
    """مسافة التحرير الكلاسيكية (stdlib فقط — بدون مكتبات خارجية)."""
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost))
        prev = cur
    return prev[-1]


def normalize(text: str) -> str:
    """تطبيع خفيف متسق مع فلسفة matching.py: توحيد الفراغات والأحرف."""
    return re.sub(r"\s+", " ", (text or "")).strip().lower()


def cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate = عدد تعديلات الأحرف / طول النص الحقيقي."""
    ref, hyp = normalize(reference), normalize(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return round(levenshtein(ref, hyp) / len(ref), 4)


def wer(reference: str, hypothesis: str) -> float:
    ref_words, hyp_words = normalize(reference).split(), normalize(hypothesis).split()
    if not ref_words:
        return 0.0 if not hyp_words else 1.0
    return round(levenshtein(" ".join(ref_words), " ".join(hyp_words)) / len(ref_words), 4)


def extract_lines(payload) -> list:
    """يستخرج نصوص السطور من استجابة سيرفر OCR بأي شكل متوقع."""
    if isinstance(payload, list):
        return [str(x) for x in payload]
    if isinstance(payload, dict):
        for key in OCR_RESPONSE_KEYS:
            if key in payload and isinstance(payload[key], list):
                return [
                    (x.get("text", "") if isinstance(x, dict) else str(x))
                    for x in payload[key]
                ]
        for v in payload.values():
            if isinstance(v, str) and len(v) > 3:
                return [v]
    return []


def ocr_image(endpoint: str, image_path: str, timeout: int = 120) -> str:
    """يرفع الصورة إلى سيرفر OCR ويعيد نص السطور مدمجاً."""
    boundary = "----AICOSBoundary"
    with open(image_path, "rb") as f:
        data = f.read()
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"{os.path.basename(image_path)}\"\r\n"
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return "\n".join(extract_lines(json.loads(resp.read().decode())))
    except urllib.error.HTTPError as e:
        print(f"  [warn] {os.path.basename(image_path)}: HTTP {e.code}")
        return ""
    except Exception as e:
        print(f"  [warn] {os.path.basename(image_path)}: {e}")
        return ""


def agg(rows: list) -> dict:
    if not rows:
        return {"n": 0, "cer": "—", "wer": "—"}
    return {
        "n": len(rows),
        "cer": round(sum(r["cer"] for r in rows) / len(rows), 4),
        "wer": round(sum(r["wer"] for r in rows) / len(rows), 4),
    }


def main():
    ap = argparse.ArgumentParser(description="OCR CER/WER evaluation for AI-COS")
    ap.add_argument("--images", required=True, help="مجلد صور الروشتات")
    ap.add_argument("--truth", required=True, help="ملف CSV: image_file,expected_text,line_type")
    ap.add_argument("--endpoint", default="http://127.0.0.1:9202/analyze")
    ap.add_argument("--out", default="ocr_eval_results.md")
    args = ap.parse_args()

    if not os.path.isfile(args.truth):
        sys.exit(f"ملف الحقيقة غير موجود: {args.truth}")

    records = []
    with open(args.truth, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if not row.get("image_file"):
                continue
            records.append({
                "file": row["image_file"].strip(),
                "expected": (row.get("expected_text") or "").strip(),
                "line_type": (row.get("line_type") or "handwritten").strip().lower(),
            })

    results = []
    for rec in records:
        path = os.path.join(args.images, rec["file"])
        if not os.path.exists(path):
            print(f"  [skip] {rec['file']}: الصورة غير موجودة")
            continue
        print(f"  ... معالجة {rec['file']} ({rec['line_type']})")
        got = ocr_image(args.endpoint, path)
        results.append({
            **rec,
            "ocr_text": normalize(got),
            "cer": cer(rec["expected"], got),
            "wer": wer(rec["expected"], got),
        })

    printed = agg([r for r in results if r["line_type"] == "printed"])
    handwritten = agg([r for r in results if r["line_type"] == "handwritten"])
    overall = agg(results)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("# نتائج تقييم دقة محرك قراءة الروشتات (CER / WER)\n\n")
        f.write("| فئة الخط | عدد العينات | CER | WER |\n|---|---|---|---|\n")
        f.write(f"| مطبوع (يُفضَّل فيه Florence-2) | {printed['n']} | {printed['cer']} | {printed['wer']} |\n")
        f.write(f"| يدوي (يُفضَّل فيه TrOCR) | {handwritten['n']} | {handwritten['cer']} | {handwritten['wer']} |\n")
        f.write(f"| **الإجمالي** | **{overall['n']}** | **{overall['cer']}** | **{overall['wer']}** |\n\n")
        f.write("*CER = نسبة أخطاء الأحرف (أقل = أفضل). المنهجية: مجموعة موصوفة يدوياً + "
                "مسافة Levenshtein على النص المطبَّع، مقابل مخرجات سيرفر OCR المحلي.*\n")

    print(f"\n✅ التقرير حُفظ في: {os.path.abspath(args.out)}")
    print(f"   مطبوع: CER={printed['cer']} ({printed['n']} عينة) | "
          f"يدوي: CER={handwritten['cer']} ({handwritten['n']} عينة) | "
          f"الإجمالي: CER={overall['cer']} ({overall['n']} عينة)")


if __name__ == "__main__":
    main()
