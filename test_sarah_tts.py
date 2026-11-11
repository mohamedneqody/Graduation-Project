import time
import os
import torch
import soundfile as sf
from voicetut_tts import VoiceTutTTS

print("PyTorch version:", torch.__version__)
print("CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("Device name:", torch.cuda.get_device_name(0))
    print("VRAM Allocated (MB):", torch.cuda.memory_allocated() / 1024**2)

model_path = r"D:\huggingface_cache\hub\models--mohammedaly22--VoiceTut-TTS\snapshots\3545fde54cfa76032acc871554fe343f3862ecb2"

t0 = time.time()
print("Loading VoiceTutTTS model...")
device = "cuda" if torch.cuda.is_available() else "cpu"
# Try loading on device
tts = VoiceTutTTS.from_pretrained(model_path, device=device, dtype="float16" if device == "cuda" else "float32")
print(f"Model loaded in {time.time() - t0:.2f}s on {device}")

text = "أهلاً بك، أنا دكتورة سارة صيدلانيتك الذكية من منصة الصيدلية، كيف أساعدك اليوم؟"
t1 = time.time()
print(f"Synthesizing text: '{text}' with speaker Sarah...")
wav = tts.synthesize(text, speaker="Sarah")
t2 = time.time()
print(f"Synthesized in {t2 - t1:.2f}s! Shape: {wav.shape}, Sample rate: {tts.sampling_rate}")

out_path = r"d:\Graduation Project\backend\uploads\test_sarah.wav"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
sf.write(out_path, wav, tts.sampling_rate)
print(f"Saved audio to: {out_path}")
