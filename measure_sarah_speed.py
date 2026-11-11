import time
import os
import torch
import soundfile as sf
from voicetut_tts import VoiceTutTTS, GenerationParams

model_path = r"D:\huggingface_cache\hub\models--mohammedaly22--VoiceTut-TTS\snapshots\3545fde54cfa76032acc871554fe343f3862ecb2"

print("CUDA available:", torch.cuda.is_available())
dev = "cuda" if torch.cuda.is_available() else "cpu"

t0 = time.time()
tts = VoiceTutTTS.from_pretrained(model_path, device=dev, dtype="float16" if dev == "cuda" else "float32")
print(f"Loaded in {time.time() - t0:.2f}s")

params = GenerationParams(num_step=16, speed=1.1)

test_sentence = "أهلاً بك، أنا دكتورة سارة من صيدلية نظام التشغيل الذكي."

for i in range(2):
    t_start = time.time()
    wav = tts.synthesize(test_sentence, speaker="Sarah", params=params)
    t_end = time.time()
    print(f"Run {i+1} took {t_end - t_start:.2f}s, wav length: {len(wav)/tts.sampling_rate:.2f}s")

out_file = r"D:\Graduation Project\AI-COS-Pharmacy\backend\uploads\sarah_sample.wav"
os.makedirs(os.path.dirname(out_file), exist_ok=True)
sf.write(out_file, wav, tts.sampling_rate)
print(f"Wrote audio sample to {out_file}")
