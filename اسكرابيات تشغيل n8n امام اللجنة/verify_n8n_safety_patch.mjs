/** Pure synthetic JS contract tests. No n8n instance, database, or messaging APIs. */
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import assert from 'node:assert/strict';

const script = fileURLToPath(new URL('../backend/scripts/prepare_n8n_safety_patch.py', import.meta.url));
const python = process.env.AICOS_TEST_PYTHON || 'python';
const fixtures = JSON.parse(execFileSync(python, [script, '--test-fixtures'], { encoding: 'utf8' }));
const now = Date.parse('2026-10-20T12:00:00Z');
class FixtureDate extends Date {
  constructor(...args) { super(...(args.length ? args : [now])); }
  static now() { return now; }
}
const entry = json => ({ json });
const context = (nodes = {}, input = {}, current = {}) => ({
  Date: FixtureDate, $json: current,
  $input: { first: () => entry(input), all: () => [entry(input)] },
  $: name => {
    if (!(name in nodes)) throw new Error(`Unexpected node read: ${name}`);
    const rows = Array.isArray(nodes[name]) ? nodes[name] : [nodes[name]];
    return { first: () => entry(rows[0]), all: () => rows.map(entry) };
  },
});
const execute = (key, nodes = {}, input = {}) =>
  runInNewContext(`(() => { ${fixtures[key]} })()`, context(nodes, input), { timeout: 1000 })?.[0]?.json;
const expression = (key, current = {}, nodes = {}) => {
  assert.ok(fixtures[key].startsWith('={{') && fixtures[key].endsWith('}}'));
  return runInNewContext(`(${fixtures[key].slice(3, -2)})`, context(nodes, {}, current), { timeout: 1000 });
};
let checks = 0;
const check = fn => { fn(); checks++; };

const finance = (rows, discount = 15) => execute('FINANCE_BUILD', {
  Webhook: { body: { proposed_discount_pct: discount } }, 'Get Customer Data': rows,
});
const measuredFinance = finance([{ customer_id: 'synthetic', full_name: '<customer>', order_count: '2', total_spent: '125.50' }]);
check(() => assert.equal(measuredFinance.historical_spend, 125.5));
check(() => assert.equal(measuredFinance.avg_order_value, 62.75));
check(() => assert.equal(measuredFinance.clv, null));
check(() => assert.equal(measuredFinance.recommendation, 'manual_review'));
check(() => assert.equal(measuredFinance.discount_approved, false));
check(() => assert.equal(finance([{error:'lookup failed'}]).historical_spend, null));
check(() => assert.equal(finance([], '15').proposed_discount_pct, null));
check(() => assert.equal(finance([{customer_id:'id', order_count:0, total_spent:0}]).historical_spend, 0));
check(() => assert.ok(expression('FINANCE_TEXT', measuredFinance).includes('&lt;customer&gt;')));
check(() => assert.equal(execute('FINANCE_PARSE', {'Calculate CLV':measuredFinance, 'Ask Ollama':{response:'DECISION:approve'}}).recommendation, 'manual_review'));

const health = (cycles = [], orders = []) => execute('HEALTH_BUILD', {
  Webhook: { body: { customer_name: '<patient>', order_count: 999 } },
  'Get Patient Orders': orders, 'Get Churn Data': cycles,
});
const missingHealth = health();
check(() => assert.equal(missingHealth.order_count, 0));
check(() => assert.ok(!missingHealth.refill_alert.includes('30')));
check(() => assert.ok(missingHealth.refill_alert.includes('لا تتوافر')));
check(() => assert.equal(health([], [{error:'database unavailable'}]).order_count, null));
for (const cycle of [
  { drug_name: 'Synthetic', last_purchase_date: 'invalid', avg_cycle_days: 30 },
  { drug_name: 'Synthetic', last_purchase_date: '2026-10-01', avg_cycle_days: null },
  { drug_name: 'Synthetic', last_purchase_date: '2026-10-01', avg_cycle_days: -1 },
  { drug_name: 'Synthetic', last_purchase_date: '2030-10-01', avg_cycle_days: 30 },
]) check(() => assert.ok(health([cycle]).refill_alert.includes('لا تتوافر')));
const estimated = health([
  { drug_name: 'Later', last_purchase_date: '2026-10-01', avg_cycle_days: 30 },
  { drug_name: 'Earlier', last_purchase_date: '2026-10-01', avg_cycle_days: 10 },
], [{ order_id: 'completed-order', status: 'completed', drugs: 'A' },
    { order_id: 'cancelled-order', status: 'cancelled', drugs: 'B' }]);
check(() => assert.equal(estimated.order_count, 1));
check(() => assert.ok(estimated.refill_alert.includes('Earlier') && estimated.refill_alert.includes('ليس جدول جرعات')));
const parsedHealth = execute('HEALTH_PARSE', {
  'Build Health Prompt': estimated,
  // Must not even read this fabricated clinical assurance.
  'Ask Ollama': { response: 'INTERACTION_CHECK: All drugs safe. AI_RECOMMENDATION: Double the dose.' },
});
check(() => assert.equal(parsedHealth.interaction_check_status, 'not_verified'));
check(() => assert.equal(parsedHealth.requires_pharmacist_review, true));
check(() => assert.ok(!JSON.stringify(parsedHealth).includes('All drugs safe')));
check(() => assert.ok(!('ollama_prompt' in parsedHealth)));
check(() => assert.ok(expression('HEALTH_TEXT', parsedHealth).includes('&lt;patient&gt;')));

const support = response => execute('SUPPORT_PARSE', {
  'Build Prompt': { full_name: 'Synthetic', customer_found: true, order_count: 2 },
  'Ask Ollama': { response },
});
for (const invalid of ['', null, 42, {}, 'TYPE:general | SEVERITY:medium | RESOLUTION:auto_reply',
  'TYPE:general | SEVERITY:made_up | RESOLUTION:auto_reply | REPLY:Hello']) {
  check(() => {
    const result = support(invalid);
    assert.equal(result.resolution, 'escalate_human');
    assert.equal(result.auto_reply_text, null);
    assert.equal(result.severity, 'unclassified');
  });
}
for (const [type, severity] of [['medication', 'low'], ['delivery', 'high'], ['general', 'critical']]) {
  check(() => assert.equal(support(`TYPE:${type} | SEVERITY:${severity} | RESOLUTION:auto_reply | REPLY:Test`).resolution, 'escalate_human'));
}
check(() => assert.equal(support('TYPE:general | SEVERITY:low | RESOLUTION:auto_reply | REPLY:Hello').resolution, 'auto_reply'));
check(() => assert.ok(expression('SUPPORT_TEXT', {customer_name:'<patient>', auto_reply_text:'<script>'}).includes('&lt;script&gt;')));

const analytics = (orders, cycles) => execute('ANALYTICS_BUILD', {
  'Orders Revenue': orders, 'Churn Risk': cycles,
  Webhook: { body: { period: 'year' } },
});
const kpis = analytics({ total_orders: '3', revenue: '125.50' }, { total_cycles: '10', at_risk: '2' });
check(() => assert.equal(kpis.period, 'last_7_days'));
check(() => assert.equal(kpis.churn_risk_customers, null));
check(() => assert.equal(kpis.overdue_cycle_count, 2));
check(() => assert.equal(kpis.overdue_cycle_rate, 0.2));
check(() => assert.equal(kpis.reminders_sent, null));
check(() => assert.equal(kpis.reminder_conversion_rate, null));
const failedKpis = analytics({ error: 'synthetic db failure' }, {});
check(() => assert.equal(failedKpis.total_orders, null));
check(() => assert.equal(failedKpis.metrics_available, false));
check(() => assert.equal(analytics({ total_orders: 0, revenue: 0 }, { total_cycles: 0, at_risk: 0 }).overdue_cycle_rate, null));
const report = execute('ANALYTICS_PARSE', { 'Merge Prompt': kpis, 'Ask Ollama': { response: null } });
check(() => assert.equal(report.llm_source, 'fallback: metrics only'));
check(() => assert.ok(!('ollama_prompt' in report)));
check(() => assert.ok(expression('ANALYTICS_TEXT', report).includes('دورات الشراء')));

const success = rows => execute('SUCCESS_BUILD', { Webhook: { body: {} }, 'Get Cycles': rows });
const noCycles = success([{ customer_id: 'synthetic', full_name: 'Synthetic', order_count: 2 }]);
check(() => assert.equal(noCycles.avg_cycle_days, null));
check(() => assert.equal(noCycles.churn_probability, null));
check(() => assert.equal(noCycles.recommended_action, 'human_review'));
const oldestCycle = success([
  { customer_id: 'synthetic', full_name: '<customer>', order_count: 2, avg_cycle_days: 30, last_purchase_date: '2026-10-15' },
  { customer_id: 'synthetic', full_name: '<customer>', order_count: 2, avg_cycle_days: 10, last_purchase_date: '2026-09-15' },
]);
check(() => assert.equal(oldestCycle.overdue_days, 25));
check(() => assert.equal(oldestCycle.observed_cycles, 2));
const successResponse = execute('SUCCESS_PARSE', { 'Calc Churn': oldestCycle, 'Ask Ollama': { response: '' } });
check(() => assert.equal(successResponse.churn_probability, null));
check(() => assert.equal(successResponse.chronic_drugs, null));
check(() => assert.ok(expression('SUCCESS_TEXT', successResponse).includes('&lt;customer&gt;')));

check(() => assert.ok(expression('ERROR_TEXT', {}).includes('غير متاح')));
const errorText = expression('ERROR_TEXT', { workflow: { name: '<workflow>' }, execution: {
  id: '42', lastNodeExecuted: '<node>', error: { message: 'PRIVATE_TOKEN_SHOULD_NOT_APPEAR' },
} });
check(() => assert.ok(errorText.includes('&lt;workflow&gt;') && !errorText.includes('PRIVATE_TOKEN')));
check(() => assert.ok(!errorText.includes('Self-Healing')));

const sla = { overdue_count: 12, requires_human_approval: true, review_threshold_hours: 24, oldest_age_hours: 28 };
check(() => assert.equal(execute('SLA_FILTER', {}, sla).sla_breached, true));
check(() => assert.equal(execute('SLA_FILTER', {}, { ...sla, overdue_count: 0 }), undefined));
check(() => assert.throws(() => execute('SLA_FILTER', {}, { ...sla, overdue_count: '12' })));
check(() => assert.ok(!expression('SLA_TEXT', sla).includes('72')));
check(() => assert.ok(expression('WEEKLY_TEXT', { estimated_savings_formatted: '<125 EGP>' }).includes('&lt;125 EGP&gt;')));
check(() => assert.ok(expression('WEEKLY_TEXT').includes('تراكمية')));
const anchor = execute('WORM_ANCHOR', {}, {body:{head_hash:'a'.repeat(64), total_lines:0, anchored_at:'<time>'}});
check(() => assert.ok(anchor.message.includes('a'.repeat(64)) && anchor.message.includes('&lt;time&gt;')));
check(() => assert.ok(anchor.message.includes('ليس تخزينًا غير قابل للتعديل')));
check(() => assert.ok(!execute('WORM_ANCHOR', {}, {body:{head_hash:'<fakehash>'}}).message.includes('<fakehash>')));
check(() => assert.ok(execute('WORM_ANCHOR', {}, {body:{total_lines:-1}}).message.includes('غير متاح')));
check(() => assert.ok(!execute('WORM_ALERT', {}, {body:{broken_lines:['<private>', 3], total_lines:null}}).message.includes('<private>')));
const emergency = expression('EMERGENCY_TEXT', {body:{customer_id:'<id>', priority:{value:1}, event_id:'<event>', timestamp:'<time>'}});
check(() => assert.ok(emergency.includes('&lt;id&gt;') && emergency.includes('&lt;event&gt;') && emergency.includes('&lt;time&gt;')));
check(() => assert.ok(emergency.includes('لم يصل تأكيد')));
check(() => assert.ok(!emergency.includes('تم توجيه المريض')));

const runId = '11111111-1111-4111-8111-111111111111';
const original = { body: { run_id: runId, attempt: 2 } };
check(() => assert.equal(execute('DISCOUNT_RUN_GUARD', {}, original), undefined));
const callback = JSON.parse(expression('DISCOUNT_CALLBACK', { run_id: 'wrong-telegram-output' }, {
  'Webhook (send_discount_offer)': original,
}));
check(() => assert.equal(callback.run_id, runId));
check(() => assert.equal(callback.attempt, 2));
for (const body of [{}, { run_id: 'auto_123' }, { run_id: runId, attempt: 0 }, { run_id: runId, attempt: '2' }]) {
  check(() => assert.throws(() => expression('DISCOUNT_CALLBACK', {}, { 'Webhook (send_discount_offer)': { body } })));
  check(() => assert.throws(() => execute('DISCOUNT_RUN_GUARD', {}, { body })));
}
console.log(JSON.stringify({ checks, notifications_sent: false, live_n8n_accessed: false }));
