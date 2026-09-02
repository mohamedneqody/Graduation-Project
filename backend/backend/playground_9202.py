import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import HTMLResponse
import sys
import os

# Add main backend to path
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.domains.prescriptions.vision import GeminiVisionProvider
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="OCR Playground")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow localhost:3000
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

vision_provider = GeminiVisionProvider()

html_content = """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <title>AI OCR Playground - Gemini 3.7 Flash</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; }
        .json-view { font-family: monospace; direction: ltr; text-align: left; background: #1e293b; color: #a5b4fc; padding: 1rem; border-radius: 0.5rem; overflow-x: auto; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <h1 class="text-3xl font-bold mb-2 text-indigo-700">💊 مساحة تجارب الموديل (OCR Playground)</h1>
        <p class="text-gray-600 mb-8">يتم تشغيل هذه الصفحة على بورت 9202 لتجربة قراءة الروشتات بشكل مباشر باستخدام <code>gemini-3.7-flash</code>.</p>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Left Column: Upload -->
            <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">1. رفع صورة الروشتة</h2>
                <input type="file" id="imageInput" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 mb-4" />
                
                <img id="previewImage" class="max-w-full rounded-lg border border-gray-200 hidden mb-4" />
                
                <button id="analyzeBtn" class="w-full bg-indigo-600 text-white font-bold py-3 rounded-lg hover:bg-indigo-700 transition disabled:opacity-50">
                    تحليل الصورة الآن (Analyze)
                </button>
                <div id="loading" class="hidden mt-4 text-center text-indigo-600 font-medium">جاري التحليل... يرجى الانتظار...</div>
            </div>

            <!-- Right Column: Results -->
            <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
                <h2 class="text-xl font-semibold mb-4 text-gray-800">2. النتيجة (Results)</h2>
                
                <div id="metrics" class="flex gap-4 mb-4 hidden">
                    <div class="bg-green-50 text-green-700 px-4 py-2 rounded-lg text-sm font-bold border border-green-200">
                        وقت الاستجابة: <span id="latencySpan"></span> ms
                    </div>
                    <div class="bg-blue-50 text-blue-700 px-4 py-2 rounded-lg text-sm font-bold border border-blue-200">
                        الموديل: <span id="modelSpan"></span>
                    </div>
                </div>

                <div id="resultsContent" class="hidden">
                    <h3 class="font-bold mb-2 text-gray-700">الأدوية المستخرجة:</h3>
                    <div class="overflow-x-auto mb-6">
                        <table class="min-w-full text-sm text-right">
                            <thead class="bg-gray-50">
                                <tr>
                                    <th class="px-4 py-2 border">الاسم (Raw)</th>
                                    <th class="px-4 py-2 border">التركيز</th>
                                    <th class="px-4 py-2 border">التعليمات</th>
                                    <th class="px-4 py-2 border">دقة القراءة</th>
                                </tr>
                            </thead>
                            <tbody id="medsTable" class="bg-white"></tbody>
                        </table>
                    </div>

                    <h3 class="font-bold mb-2 text-gray-700">النتيجة الخام (Raw JSON):</h3>
                    <pre id="jsonOutput" class="json-view"></pre>
                </div>
            </div>
        </div>
    </div>

    <script>
        const imageInput = document.getElementById('imageInput');
        const previewImage = document.getElementById('previewImage');
        const analyzeBtn = document.getElementById('analyzeBtn');
        const loading = document.getElementById('loading');
        const resultsContent = document.getElementById('resultsContent');
        const metrics = document.getElementById('metrics');
        
        let selectedFile = null;

        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                selectedFile = file;
                const reader = new FileReader();
                reader.onload = (e) => {
                    previewImage.src = e.target.result;
                    previewImage.classList.remove('hidden');
                }
                reader.readAsDataURL(file);
            }
        });

        analyzeBtn.addEventListener('click', async () => {
            if (!selectedFile) {
                alert('الرجاء اختيار صورة أولاً');
                return;
            }

            analyzeBtn.disabled = true;
            loading.classList.remove('hidden');
            resultsContent.classList.add('hidden');
            metrics.classList.add('hidden');

            const formData = new FormData();
            formData.append('file', selectedFile);

            try {
                const response = await fetch('/api/analyze', {
                    method: 'POST',
                    body: formData
                });
                
                if (!response.ok) {
                    const err = await response.text();
                    throw new Error(err);
                }
                
                const data = await response.json();
                
                // Show metrics
                document.getElementById('latencySpan').innerText = data.metadata.latency_ms || 'N/A';
                document.getElementById('modelSpan').innerText = data.metadata.model_version || 'N/A';
                metrics.classList.remove('hidden');

                // Render Table
                const tbody = document.getElementById('medsTable');
                tbody.innerHTML = '';
                const meds = data.parsed.medications || [];
                meds.forEach(med => {
                    const row = `<tr>
                        <td class="px-4 py-2 border font-medium text-indigo-900">\\${med.raw_name || '-'}</td>
                        <td class="px-4 py-2 border text-gray-600">\\${med.strength || '-'}</td>
                        <td class="px-4 py-2 border text-gray-600">\\${med.instructions || '-'}</td>
                        <td class="px-4 py-2 border text-gray-600">\\${med.ocr_confidence ? (med.ocr_confidence * 100).toFixed(0) + '%' : '-'}</td>
                    </tr>`;
                    tbody.innerHTML += row;
                });

                // Render JSON
                document.getElementById('jsonOutput').innerText = JSON.stringify(data, null, 2);
                resultsContent.classList.remove('hidden');

            } catch (error) {
                alert('حدث خطأ أثناء التحليل: ' + error.message);
                console.error(error);
            } finally {
                analyzeBtn.disabled = false;
                loading.classList.add('hidden');
            }
        });
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def get_index():
    return html_content

@app.post("/api/analyze")
async def analyze(file: UploadFile = File(...)):
    try:
        content = await file.read()
        parsed, metadata = await vision_provider.analyze_image(content, file.content_type)
        return {
            "parsed": parsed.model_dump(),
            "metadata": metadata.model_dump()
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e) + "\n\n" + traceback.format_exc())

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=9202)
