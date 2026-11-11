"""Audit-only runner: no remote network; no live DB or background service credentials."""
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT / 'AI-COS-Pharmacy' / 'backend')
sys.path.insert(0, str(Path.cwd()))
os.environ.update({
    'DATABASE_URL': 'postgresql+asyncpg://audit:audit@127.0.0.1:1/audit_unreachable',
    'TEST_DATABASE_URL': 'postgresql+asyncpg://audit:audit@127.0.0.1:56432/pharmacy_test',
    'RUN_POSTGRES_TESTS': '0', 'RUN_LIVE_TESTS': '0',
    'NEXT_PUBLIC_SUPABASE_URL': 'http://127.0.0.1:1',
    'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY': 'audit-placeholder',
    'SUPABASE_SERVICE_ROLE_KEY': '', 'GEMINI_API_KEY': '', 'GEMINI_API_KEYS': '',
    'OPENROUTER_API_KEY': '', 'N8N_WEBHOOK_URL': 'http://127.0.0.1:1',
    'N8N_SERVICE_KEY': 'audit-placeholder', 'INTERNAL_SERVICE_KEY': 'audit-placeholder',
    'INTERNAL_OCR_SECRET': 'audit-placeholder', 'LOCAL_OCR_URL': 'http://127.0.0.1:1',
    'OLLAMA_URL': 'http://127.0.0.1:1/api/generate', 'REDIS_URL': 'redis://127.0.0.1:1',
    'ENVIRONMENT': 'dev', 'HF_HUB_OFFLINE': '1', 'TRANSFORMERS_OFFLINE': '1',
})

def deny_remote(event, args):
    if event == 'socket.connect':
        address = args[1]
        if isinstance(address, tuple) and address[0] not in ('127.0.0.1', '::1', 'localhost'):
            raise OSError('Remote network disabled during academic audit')

sys.addaudithook(deny_remote)
import pytest
raise SystemExit(pytest.main(['tests', '-q', '--tb=short', '--disable-warnings',
    '--junitxml=' + str(Path(__file__).with_name('backend_tests.xml'))]))
