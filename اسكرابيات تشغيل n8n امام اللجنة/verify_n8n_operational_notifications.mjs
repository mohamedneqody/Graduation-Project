// Synthetic embedded-JavaScript checks. No n8n, network, real data, or sends.
import assert from 'node:assert/strict';
let stdin = '';
for await (const chunk of process.stdin) stdin += chunk;
const c = JSON.parse(stdin);
let checks = 0;
const eq = (a,b) => {assert.deepEqual(a,b); checks++;};
const throws = f => {assert.throws(f); checks++;};
const run = '11111111-1111-4111-8111-111111111111';
const tenant = '22222222-2222-4222-8222-222222222222';
const token = '33333333-3333-4333-8333-333333333333';
const node = context => name => {
  if (!(name in context)) throw Error('Node did not run');
  return {first:()=>({json:context[name]})};
};
const code = (source, data, context={}) => new Function('$input','$',source)({first:()=>({json:data})}, node(context));
const expr = (source, data, context={}) => new Function('$json','$',`return (${source.slice(3,-2)});`)(data, node(context));
const parent = {run_id:run,tenant_id:tenant,workflow_name:'order-notification',attempt:1};
eq(code(c.VALIDATE_REQUEST,{body:parent})[0].json,parent);
eq(code(c.VALIDATE_REQUEST,{body:{...parent,workflow:'order-notification',message:'untrusted',chatId:'untrusted'}})[0].json,parent);
eq(code(c.VALIDATE_REQUEST,{body:{...parent,is_test:true}})[0].json,{...parent,requested_is_test:true});
for (const body of [undefined,null,[],{}, {...parent,run_id:'auto_123'}, {...parent,run_id:[run]},
  {...parent,tenant_id:''}, {...parent,tenant_id:[tenant]}, {...parent,attempt:'1'},
  {...parent,attempt:0}, {...parent,attempt:1.5}, {...parent,attempt:true}, {...parent,attempt:Number.MAX_SAFE_INTEGER+1},
  {...parent,workflow_name:'low-stock'}, {...parent,workflow:'inventory-alert'}, {...parent,is_test:'true'},
  {...parent,is_test:1}]) throws(()=>code(c.VALIDATE_REQUEST,{body}));
eq(expr(c.CLAIM_BODY,parent),{attempt:1,workflow_name:'order-notification'});
const claim = {claimed:true,...parent,claim_token:token,is_test:false,message:'AI-COS — synthetic <event>&'};
const ctx = {'Validate Notification Request':parent};
const valid = code(c.VALIDATE_CLAIM,claim,ctx)[0].json;
eq(valid,claim);
eq(code(c.VALIDATE_CLAIM,{claimed:false},ctx)[0].json,{claimed:false});
for (const value of [{},null,{claimed:'true'}, {...claim,claimed:1}, {...claim,run_id:tenant},
  {...claim,tenant_id:run}, {...claim,workflow_name:'low-stock'}, {...claim,attempt:2},
  {...claim,claim_token:'x'}, {...claim,claim_token:[token]}, {...claim,is_test:'false'},
  {...claim,is_test:null}, {...claim,message:''}, {...claim,message:'  '}, {...claim,message:null},
  {...claim,message:'x'.repeat(3001)}, {...claim,is_test:true}]) throws(()=>code(c.VALIDATE_CLAIM,value,ctx));
const testClaim = {...claim,is_test:true,message:'اختبار AI-COS'};
eq(code(c.VALIDATE_CLAIM,testClaim,ctx)[0].json,testClaim);
throws(()=>code(c.VALIDATE_CLAIM,claim,{'Validate Notification Request':{...parent,requested_is_test:true}}));
throws(()=>code(c.VALIDATE_CLAIM,testClaim,{'Validate Notification Request':{...parent,requested_is_test:false}}));
const validCtx = {'Validate Notification Claim':valid};
eq(expr(c.TELEGRAM_TEXT,{},validCtx),'AI-COS — synthetic &lt;event&gt;&amp;');
eq(expr(c.TELEGRAM_TEXT,{}, {'Validate Notification Claim':testClaim}),'اختبار AI-COS');
throws(()=>expr(c.TELEGRAM_TEXT,{}, {'Validate Notification Claim':{claimed:false}}));
for (const response of [{message_id:123},{ok:true,result:{message_id:456}}]) {
  const result = code(c.COMPLETE_BODY,response,validCtx)[0].json;
  eq(result.status,'delivered'); eq(result.message_id,String(response.message_id ?? response.result.message_id));
  eq(result.run_id,run); eq(result.attempt,1); eq(result.workflow_name,'order-notification'); eq(result.claim_token,token);
  const body = expr(c.COMPLETION_REQUEST,result);
  eq(body,{attempt:1,workflow_name:'order-notification',claim_token:token,status:'delivered',message_id:result.message_id});
}
for (const response of [{},{error:'timeout'},{message_id:0},{message_id:-1},{message_id:1.5},{message_id:'123'},
  {error:'failure',message_id:123},{ok:false,result:{message_id:123}}, {message_id:Number.MAX_SAFE_INTEGER+1}]) {
  const result = code(c.COMPLETE_BODY,response,validCtx)[0].json;
  eq(result.status,'delivery_unknown'); eq(result.message_id,null);
}
throws(()=>code(c.COMPLETE_BODY,{message_id:1},{'Validate Notification Claim':{claimed:false}}));
// Replay a mocked atomic service claim: only the first committed true response may send.
let claimed = false, syntheticSends = 0;
for (let i=0;i<3;i++) {
  const answer = claimed ? {claimed:false} : claim;
  claimed = true;
  const result = code(c.VALIDATE_CLAIM,answer,ctx)[0].json;
  if (result.claimed === true) {expr(c.TELEGRAM_TEXT,{}, {'Validate Notification Claim':result}); syntheticSends++;}
}
eq(syntheticSends,1);
process.stdout.write(JSON.stringify({checks,passed:true,network:false})+'\n');
