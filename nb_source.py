# ============================================================
# Cell 1: Install Required Libraries
# ============================================================
!pip install -q transformers datasets accelerate peft trl bitsandbytes sentencepiece huggingface_hub
# ============================================================
# Cell 2: Verify GPU is Available
# ============================================================
import torch

print("CUDA Available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("GPU:", torch.cuda.get_device_name(0))
    print("VRAM:", round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 2), "GB")
else:
    print("⚠️ Warning: No GPU found. Please enable GPU in Colab (Runtime > Change runtime type > T4 GPU)")
# ============================================================
# Cell 3: Upload Dataset Files (train.jsonl & validation.jsonl)
# ============================================================
from google.colab import files
import os

print("Please upload train.jsonl and validation.jsonl:")
uploaded = files.upload()

for fname in ["train.jsonl", "validation.jsonl"]:
    if os.path.exists(fname):
        lines = sum(1 for _ in open(fname, encoding="utf-8"))
        print(f"✅ {fname} ready: {lines} samples")
    else:
        print(f"❌ ERROR: {fname} missing!")
# ============================================================
# Cell 4: Load Base Model (Qwen 2.5 3B / 7B) with 4-bit Quantization
# ============================================================
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import torch

model_id = "Qwen/Qwen2.5-3B-Instruct"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    torch_dtype=torch.float16,
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    torch_dtype=torch.float16,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

model.config.use_cache = False
print("✅ Qwen 2.5 loaded successfully!")
print(f"VRAM allocated: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")
# ============================================================
# Cell 5: Load and Format Dataset with Qwen ChatML Template
# ============================================================
from datasets import load_dataset

dataset = load_dataset(
    "json",
    data_files={
        "train": "train.jsonl",
        "validation": "validation.jsonl",
    },
)

def format_chat(example):
    return {
        "text": tokenizer.apply_chat_template(
            example["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
    }

train_dataset = dataset["train"].map(format_chat)
validation_dataset = dataset["validation"].map(format_chat)

print("✅ Dataset formatted successfully! Sample:")
print(train_dataset[0]["text"][:350], "...")
# ============================================================
# Cell 6: Configure LoRA specifically optimized for Qwen 2.5
# ============================================================
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

model = prepare_model_for_kbit_training(model)

peft_config = LoraConfig(
    r=64,
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)

model = get_peft_model(model, peft_config)
model.print_trainable_parameters()
# ============================================================
# Cell 7: Training Configuration (SFTConfig for modern TRL)
# ============================================================
from trl import SFTConfig

training_args = SFTConfig(
    output_dir="./ai-cos-qwen-lora",
    num_train_epochs=3,
    learning_rate=1e-4,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4,
    max_grad_norm=0.3,
    logging_steps=10,
    eval_strategy="epoch",
    save_strategy="epoch",
    fp16=True,
    gradient_checkpointing=True,
    optim="paged_adamw_32bit",
    report_to="none",
    dataset_text_field="text",
    max_seq_length=2048,
)

print("✅ SFTConfig configured successfully!")
# ============================================================
# Cell 8: Initialize and Start SFTTrainer
# ============================================================
from trl import SFTTrainer

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=validation_dataset,
    processing_class=tokenizer,
)

print("🚀 Starting Training for AI-COS Pharmacy Qwen 2.5...")
trainer.train()
# ============================================================
# Cell 9: Save LoRA Adapters & Tokenizer
# ============================================================
save_dir = "./ai-cos-qwen-final"
trainer.save_model(save_dir)
tokenizer.save_pretrained(save_dir)

print(f"✅ Model saved locally to {save_dir}")
# ============================================================
# Cell 10: Quick Test - University, Creator & Pharmacy Persona
# ============================================================
import torch

test_prompts = [
    "مين اللي عمل هذا المشروع؟",
    "مشروع صيدلية AI-COS تابع لأي جامعة وكلية؟",
    "أنا عندي صداع بسيط، هل أقدر آخذ مسكن إيبوبروفين مع كونكور؟"
]

for p in test_prompts:
    messages = [
        {"role": "system", "content": "You are an AI customer support assistant for AI-COS Pharmacy — an intelligent, AI-powered online pharmacy platform. You help customers, store owners, and staff with questions about the pharmacy system including: account registration, drug ordering, AI reminders, drug interaction checks, the RAG chatbot, the analytics dashboard, n8n automation workflows, and AI governance features. Always be professional, warm, and helpful. For any medical advice questions, always add the disclaimer: 'Please consult your pharmacist or doctor for medical advice.'"},
        {"role": "user", "content": p}
    ]
    prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_new_tokens=250, temperature=0.7, do_sample=True, pad_token_id=tokenizer.eos_token_id)
    response = tokenizer.decode(outputs[0][inputs['input_ids'].shape[1]:], skip_special_tokens=True)
    print(f"\n❓ السؤال: {p}")
    print(f"🤖 الرد:\n{response}")
    print("-" * 50)
# ============================================================
# Cell 11: Export / Merge to Google Drive
# ============================================================
from google.colab import drive
import shutil
import os

drive.mount('/content/drive')
drive_path = "/content/drive/MyDrive/AI-COS-Qwen-Final"
os.makedirs(drive_path, exist_ok=True)
shutil.copytree("./ai-cos-qwen-final", drive_path, dirs_exist_ok=True)
print(f"🎉 Model successfully exported to Google Drive: {drive_path}")