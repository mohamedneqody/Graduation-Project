/** Execute only pure message expressions; never connect to n8n or send messages. */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import assert from 'node:assert/strict';

const root = new URL('../docs/n8n/', import.meta.url);
const offer = {
  tenant_id: '11111111-1111-4111-8111-111111111111',
  customer_id: '22222222-2222-4222-8222-222222222222',
  drug_id: '33333333-3333-4333-8333-333333333333',
  coupon_id: '44444444-4444-4444-8444-444444444444',
  customer_name: 'Synthetic <customer>', drug_name: 'Synthetic <product>',
  coupon_code: 'C123', coupon_persisted: true, discount_pct: 17,
  expires_at: new Date(Date.now() + 3600000).toISOString(),
};
let checks = 0;
for (const file of ['workflow_send_discount_offer.json', 'workflow_6_send_discount_offer.json']) {
  const workflow = JSON.parse(readFileSync(fileURLToPath(new URL(file, root)), 'utf8'));
  const code = workflow.nodes.find(node => node.parameters?.jsCode)?.parameters.jsCode;
  assert.ok(code);
  const execute = body => new Function('$input', code)({ first: () => ({ json: { body } }) });
  const message = execute(offer)[0].json.message;
  assert.ok(message.includes('17%') && message.includes('C123'));
  assert.ok(message.includes('&lt;product&gt;') && !message.includes('<product>'));
  assert.ok(message.includes('\n'), 'Message needs actual line breaks');
  checks++;
  for (const patch of [{ coupon_persisted: false }, { customer_id: null }, { drug_id: null },
    { coupon_id: null }, { discount_pct: 17.5 }, { discount_pct: 101 },
    { expires_at: '2000-01-01' }, { coupon_code: '' }]) {
    assert.throws(() => execute({ ...offer, ...patch })); checks++;
  }
}
const workflow = JSON.parse(readFileSync(fileURLToPath(new URL('workflow_governance_reminders_final.json', root)), 'utf8'));
const expression = workflow.nodes.find(node => node.parameters?.text?.includes('const eligible'))?.parameters.text;
assert.ok(expression?.startsWith('={{') && expression.endsWith('}}'));
const render = campaign => new Function('$', 'return (' + expression.slice(3, -2) + ')')(name => ({
  item: { json: name === '1. Pull Pending Reminders' ? offer : campaign },
}));
assert.ok(render(offer).includes('17%'));
for (const campaign of [{ ...offer, coupon_persisted: false }, { ...offer, customer_id: offer.drug_id },
  { ...offer, drug_id: offer.customer_id }, { ...offer, expires_at: '2000-01-01' }]) {
  assert.ok(!render(campaign).includes('C123')); checks++;
}
console.log(JSON.stringify({ checks: checks + 1, notifications_sent: false, live_n8n_accessed: false }));
