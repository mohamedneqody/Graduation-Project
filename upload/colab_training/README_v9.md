# جولة التدريب v9 - بانضباط الفصل والقياس الصادق

1. ارفع لجلسة Colab: upload_v9_train.zip + upload_v9_eval_frozen.zip (+ اختياري v8 الموجهة)
2. شغل finetune_colab_v9.py (T4 حوالي 25-40 دقيقة)
3. القياس الختامي على holdout_frozen_v1 فقط - قارن مع خط الأساس 0.2827
4. انزل بالنموذج الفائز -> استبدل trocr-finetuned-final -> شغل eval_reading_ab.py محلياً للتثبيت

قواعد صارمة: holdout_frozen_v1 محظور على التدريب إلى الأبد - أي نتيجة لمسته تعتبر ملغاة.
