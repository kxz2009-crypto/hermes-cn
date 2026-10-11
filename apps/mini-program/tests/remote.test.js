const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function setup({enabled=true,paid=false,cancel=false}={}){
 let native=0;const calls=[];const original='{"offerId":"1450674694", "goodsPrice":990}';
 const wx={getSystemInfoSync:()=>({platform:'android'}),canIUse:()=>true,login:o=>o.success({code:'login'}),
 request:o=>{calls.push(o);let data;
 if(o.url.endsWith('/auth/login'))data={token:'bearer'};
 else if(o.url.endsWith('/pay-params'))data={mode:'short_series_goods',signData:original,paySig:'p',signature:'s'};
 else if(o.url.endsWith('/confirm'))data={id:'h1',paymentStatus:paid?'paid':'pending'};
 else data=[];
 o.success({statusCode:200,data});},
 requestVirtualPayment:o=>{native++;assert.equal(o.signData,original);assert.equal(o.paySig,'p');cancel?o.fail({errMsg:'cancel'}):o.success({errMsg:'ok'});}
 };
 const m={exports:{}};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../services/remote.js'),'utf8'),
 {module:m,wx,Promise,Error,setTimeout:f=>f(),encodeURIComponent,require:n=>n==='../config/env'?{apiBase:'https://example.test',realPaymentEnabled:enabled}:{PRODUCT:{id:'hermes_install_990'}}});
 return {a:m.exports,calls,native:()=>native};
}
test('原样传支付签名，客户端成功仍等待服务端确认',async()=>{const s=setup();const o=await s.a.pay('h1');assert.equal(o.paymentStatus,'pending');assert.equal(s.native(),1);assert.equal(s.calls.filter(x=>x.url.endsWith('/confirm')).length,5);});
test('服务端确认后才返回已支付',async()=>{const s=setup({paid:true});assert.equal((await s.a.pay('h1')).paymentStatus,'paid');});
test('取消与已到账竞争时以服务端结果为准',async()=>{const s=setup({cancel:true,paid:true});assert.equal((await s.a.pay('h1')).paymentStatus,'paid');});
test('取消未到账保留原订单并提示取消',async()=>{const s=setup({cancel:true});await assert.rejects(s.a.pay('h1'),{code:'PAYMENT_CANCELLED'});});
test('未启用支付不拉起接口',async()=>{const s=setup({enabled:false});await assert.rejects(s.a.pay('h1'),{code:'PAYMENT_DISABLED'});assert.equal(s.native(),0);});
test('退款提交仅发申请，不在客户端改为已退款',async()=>{const s=setup();await s.a.refund('h1','无法使用');const r=s.calls.find(x=>x.url.endsWith('/refund'));assert.equal(r.data.reason,'无法使用');assert.equal(s.native(),0);});
