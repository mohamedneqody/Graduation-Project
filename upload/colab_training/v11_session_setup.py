# -*- coding: utf-8 -*-
"""خلية إعداد جلسة A100 الجديدة — شغّلها كأول خلية بعد تغيير الـruntime."""
import os
from google.colab import drive
drive.mount('/content/drive')
MD = "/content/drive/MyDrive"

print("=== تثبيت النسخة المستقرة ===")
import subprocess
r = subprocess.run(["pip", "-q", "install", "transformers==4.46.3", "evaluate", "jiwer", "faker"],
               capture_output=True, text=True)
print("pip done")

import os, shutil, zipfile
print("=== استخراج كل شيء من Drive ===")
os.makedirs("/content/data_v11", exist_ok=True)

# 1) الداتا المتولدة (المحفوظة من الجلسة السابقة)
with zipfile.ZipFile(MD + "/v11_gen_data.zip") as z:
    z.extractall("/content/data_v11/messy_grand")
print("gen data restored:", len(os.listdir("/content/data_v11/messy_grand/line_crops")), "crops")

# 2) الـholdout
with zipfile.ZipFile(MD + "/upload_v9_eval_frozen.zip") as z:
    z.extractall("/content/data_v11/holdout")
print("holdout restored")

# 3) أوزان v9
with zipfile.ZipFile(MD + "/upload_v9_model.zip") as z:
    z.extractall("/content/data_v11/v9model")
print("v9 weights restored")

# 4) السكربت المحدّث
shutil.copy(MD + "/finetune_colab_v11.py", "/content/finetune_colab_v11.py")
print("script ready ✓")
print("=" * 50)
print("الآن شغّل الخلية التالية:  !python finetune_colab_v11.py")
