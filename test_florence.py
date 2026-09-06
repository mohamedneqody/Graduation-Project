import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from PIL import Image, ImageDraw

# Add upload folder to path
sys.path.append(r"D:\Graduation Project\upload")
from prescription_ocr_engine import PrescriptionOCREngine

def main():
    if len(sys.argv) > 1:
        img_path = sys.argv[1]
    else:
        default_img = r"D:\مشروع تخرج\files\nearmiss_01.jpg"
        if os.path.exists(default_img):
            img_path = default_img
        else:
            img_path = input("Enter prescription image path: ").strip(' "\'')

    if not os.path.exists(img_path):
        print(f"[Error] Image not found: {img_path}")
        return

    print("\n" + "=" * 60)
    print("   AI-COS HYBRID OCR ENGINE (Florence-2 + TrOCR Fine-Tuned)")
    print("=" * 60)
    print(f"📁 Image: {img_path}")
    
    # 1. Initialize Engine
    print("\n⏳ Loading Hybrid OCR Engine...")
    engine = PrescriptionOCREngine()
    
    # 2. Run End-to-End Hybrid Processing
    print("🔍 Processing prescription (Florence-2 layout + TrOCR decoding)...")
    result = engine.process_prescription(img_path, use_florence=True)

    medications = result.get("medications", [])
    print(f"\n✅ Detection Complete! Total Lines Found: {len(medications)}")
    print("=" * 60)

    # 3. Visualization
    orig_img = Image.open(img_path).convert("RGB")
    annotated_img = orig_img.copy()
    draw = ImageDraw.Draw(annotated_img)

    for idx, med in enumerate(medications, 1):
        f_text = med.get("florence_text", "")
        t_text = med.get("trocr_text", "")
        final_name = med.get("raw_name", "")
        bbox = med.get("bbox")

        print(f"\n[Line {idx}]")
        print(f"  🤖 Florence-2 Vision:  {f_text}")
        print(f"  ✍️ TrOCR Fine-Tuned:   {t_text}")
        print(f"  💊 Final Medication:   {final_name}")

        if bbox and len(bbox) == 4:
            y1, x1, y2, x2 = bbox
            draw.rectangle([x1, y1, x2, y2], outline="#00E676", width=3)

    print("\n" + "=" * 60)
    out_dir = os.path.dirname(img_path)
    output_path = os.path.join(out_dir, "florence_trocr_result.jpg")
    try:
        annotated_img.save(output_path)
        print(f"🖼️ Bounding box image saved to:")
        print(f"   {output_path}\n")
    except Exception as e:
        print(f"[Warning] Could not save annotated image: {e}")

if __name__ == "__main__":
    main()
