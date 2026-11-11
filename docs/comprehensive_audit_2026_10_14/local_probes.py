"""Reproduce audit findings using synthetic values and mocks, without service calls."""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT / 'AI-COS-Pharmacy/backend')
sys.path.insert(0, str(Path.cwd()))
os.environ['DATABASE_URL'] = 'postgresql+asyncpg://audit:audit@127.0.0.1:1/audit'
os.environ['ENVIRONMENT'] = 'dev'

async def main():
    results = {}
    from app.domains.accounting.working_capital import get_working_capital_analysis
    for payable in (1000, 10000):
        db = AsyncMock()
        rows = MagicMock()
        rows.fetchall.return_value = [
            ('101', 'cash', 'ASSET', 30000, 0),
            ('102', 'inventory', 'ASSET', 20000, 0),
            ('202', 'payable', 'LIABILITY', 0, payable),
            ('401', 'revenue', 'REVENUE', 0, 100000),
        ]
        db.execute.return_value = rows
        data = await get_working_capital_analysis(db, uuid4())
        results[f'ccc_payable_{payable}'] = data['cash_conversion_cycle']

    from app.domains.agents import pricing
    args = dict(customer_name='Synthetic audit customer', churn_probability=.1,
                order_count=10, total_spent=10000, drug_category='chronic')
    with patch.object(pricing, 'execute_tiered_llm', AsyncMock(return_value=(None, 'offline'))):
        fallback = await pricing.calculate_pricing_discount(**args)
    with patch.object(pricing, 'execute_tiered_llm', AsyncMock(return_value=(
        json.dumps({'discount_percentage': 5, 'rationale': 'synthetic'}), 'mock'))):
        generated = await pricing.calculate_pricing_discount(**args)
    results['pricing_same_inputs'] = {'deterministic_fallback_discount': fallback['discount_percentage'],
        'llm_proposed_discount': generated['discount_percentage']}

    from app.domains.prediction import service as prediction
    feature_data = {'features': {}, 'avg_cycle': 30, 'is_cold_start': True, 'drug_name': 'Synthetic'}
    model = MagicMock()
    model.predict.return_value = [30.0]
    with patch.object(prediction, '_build_features', AsyncMock(return_value=feature_data)), \
         patch.object(prediction, '_load', return_value=model), \
         patch.object(prediction, '_get_shap_top3', return_value=[]):
        try:
            await prediction.predict_cycle(AsyncMock(), uuid4(), uuid4())
            results['cold_start'] = 'returned normally'
        except Exception as exc:
            results['cold_start'] = {'type': type(exc).__name__, 'message': str(exc)}

    from app.domains.insights.router import _rfm_scores, _segment
    scores = _rfm_scores(400, 4, 100)
    results['rfm_old_customer'] = {'days_since_purchase': 400, 'orders': 4,
        'scores': scores, 'segment': _segment(**scores)}
    results['rfm_zero_day_conversion'] = float(0 or 999)

    from app.domains.ai.math_engine import DeterministicMathEngine
    trusted_chunk = {'source_type': 'database_catalog', 'content': 'اسم الدواء: Panadol\nالسعر الأساسي: 20.00'}
    results['math_contract_recheck'] = {
        'arabic_quantity': DeterministicMathEngine.extract_and_solve_math('احسب ٣ علب Panadol مع CARE15', [trusted_chunk]),
        'strength_not_quantity': DeterministicMathEngine.extract_and_solve_math('احسب Panadol 500 mg', [trusted_chunk]),
    }

    from app.domains.ai.response_verifier import prepare_context, verify_answer
    chunks = prepare_context([{'source_type': 'clinical_reference', 'content': 'Store medicines as directed on the label.'}])
    # Harmless, demonstrably unsupported claim: illustrates provenance != entailment.
    raw = json.dumps({'decision': 'answer', 'reply': 'The store closes every Tuesday.',
                      'source_ids': [chunks[0]['source_id']]})
    _, verdict = verify_answer(raw, chunks)
    results['unsupported_claim_with_valid_source_id'] = verdict

    from app.core import worm_ledger as worm
    with tempfile.TemporaryDirectory(prefix='aicos-audit-') as tmp:
        path = str(Path(tmp) / 'isolated_ledger.jsonl')
        with patch.object(worm, 'LEDGER_PATH', path), patch.object(worm, '_LOCK_PATH', path+'.lock'):
            worm.append_entry('synthetic-event-1', '2026-10-14', 'original-payload-hash')
            first = worm.read_ledger()[0]
            first['payload_hash'] = 'changed-payload-hash'
            first['line_hash'] = worm._line_hash(first['prev'], first['event_id'], first['payload_hash'], first['created_at'])
            Path(path).write_text(json.dumps(first)+'\n', encoding='utf-8')
            results['rewritten_temp_ledger'] = worm.verify_file_integrity()

    from app.domains.order import service as orders
    tenant_id, order_id, customer_id = uuid4(), uuid4(), uuid4()
    order = MagicMock(order_id=order_id, tenant_id=tenant_id, customer_id=customer_id, status='pending')
    db = AsyncMock()
    row = MagicMock()
    row.scalars.return_value.first.return_value = order
    db.execute.return_value = row
    with patch.object(orders, '_build_order_out', AsyncMock(return_value={'status': 'completed'})):
        await orders.update_order_status(db, order_id, 'completed', tenant_id)
    results['pending_complete_without_rx_recheck'] = {'status': order.status, 'db_queries': db.execute.await_count,
        'commit_count': db.commit.await_count}

    output = Path(__file__).with_name('local_probes.json')
    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(results, ensure_ascii=True, indent=2))

asyncio.run(main())
