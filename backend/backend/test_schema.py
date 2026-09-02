import asyncio
import sys
sys.path.append(r"D:\Graduation Project\backend\backend")
from app.domains.prescriptions.vision import PrescriptionVisionOutput
import json

print(json.dumps(PrescriptionVisionOutput.model_json_schema(), indent=2))
