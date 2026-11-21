// Pure JavaScript execution with synthetic inputs; never loads n8n or sends HTTP.
import assert from 'node:assert/strict';
let stdin = '';
for await (const chunk of process.stdin) stdin += chunk;
const c = JSON.parse(stdin);
let checks = 0;
const eq = (a,b) => {assert.deepEqual(a,b); checks++;};
const throws = f => {assert.throws(f); checks++;};
const uuid = '11111111-1111-4111-8111-111111111111';
const input = json => ({first:()=>({json}),all:()=>[{json}]});
const code = (source, data, context={}) => new Function('$input','$',source)(input(data), name => {
  if (!(name in context)) throw Error('Node did not run');
  return {first:()=>({json:context[name]}),item:{json:context[name]}};
});
const expr = (source,data,context={}) => new Function('$json','$',`return (${source.slice(3,-2)});`)(data, name => {
  if (!(name in context)) throw Error('Node did not run');
  return {first:()=>({json:context[name]}),item:{json:context[name]}};
});
const parent = {run_id:uuid,tenant_id:uuid,attempt:1};
eq(code(c.VALIDATE_REQUEST,{body:parent})[0].json,parent);
for (const body of [{}, {...parent,run_id:'auto_123'}, {...parent,attempt:'1'}, {...parent,attempt:0}, {...parent,tenant_id:''}]) {
  throws(()=>code(c.VALIDATE_REQUEST,{body}));
}
eq(code(c.NORMALIZE_QUEUE,{})[0].json,{skip:true});
eq(code(c.NORMALIZE_QUEUE,[])[0].json,{skip:true});
eq(code(c.NORMALIZE_QUEUE,[{reminder_id:uuid,decision:'human_review',status:'pending'}])[0].json,{skip:true});
eq(code(c.NORMALIZE_QUEUE,[{reminder_id:uuid,decision:'approved',status:'dispatching'}])[0].json,{skip:true});
eq(code(c.NORMALIZE_QUEUE,[{reminder_id:uuid,decision:'approved',status:'pending'}])[0].json,{reminder_id:uuid});
eq(expr(c.CLAIM_BODY,{}),{});
eq(expr(c.CLAIM_BODY,{}, {'Validate Reminder Request':parent}),{parent_run_id:uuid,parent_attempt:1});
const claim = {claimed:true,run_id:uuid,claim_token:uuid,reminder:{reminder_id:uuid,customer_name:'<script>&',drug_name:'A&B'}};
const ctx = {'Claim Reminder':claim};
const msg = expr(c.REMINDER_TEXT,{},ctx);
assert(msg.includes('&lt;script&gt;&amp;') && msg.includes('A&amp;B') && !msg.includes('<script>')); checks++;
throws(()=>expr(c.REMINDER_TEXT,{}, {'Claim Reminder':{...claim,claimed:false}}));
for (const data of [{message_id:123},{result:{message_id:456}}]) {
  const result=code(c.COMPLETE_BODY,data,ctx)[0].json;
  eq(result.status,'delivered'); eq(result.run_id,uuid); eq(result.claim_token,uuid);
  eq(result.message_id,String(data.message_id || data.result.message_id));
}
for (const data of [{},{error:'timeout'},{message_id:0},{message_id:'123'},{error:'failure',message_id:123}]) {
  const result = code(c.COMPLETE_BODY,data,ctx)[0].json;
  eq(result.status,'delivery_unknown'); eq(result.message_id,null);
}
eq(code(c.SCAN_COMPLETE,{message_id:123}),[]);
eq(code(c.SCAN_COMPLETE,{}, {'Validate Reminder Request':parent})[0].json.status,'processing_completed');
eq(code(c.RECALC_QUEUED,{task_id:'synthetic'}, {'Validate Evaluation Request':parent})[0].json.status,'processing_queued');
for (const data of [{},{error:'failed',task_id:'synthetic'},{task_id:12}]) {
  throws(()=>code(c.RECALC_QUEUED,data, {'Validate Evaluation Request':parent}));
}
process.stdout.write(JSON.stringify({checks,passed:true,network:false})+'\n');
