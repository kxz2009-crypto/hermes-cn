
const test=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
function harness(){
 const root=path.resolve(__dirname,'..'),cache=new Map(),storage=new Map(),routes=[];
 let definition;
 const wx={getStorageSync:k=>storage.has(k)?JSON.parse(storage.get(k)):undefined,setStorageSync:(k,s)=>storage.set(k,JSON.stringify(s)),
 navigateTo:o=>routes.push(o.url),redirectTo:o=>routes.push(o.url),setClipboardData:()=>{},scanCode:()=>{},showModal:o=>o.success({confirm:true})};
 function load(file){file=path.resolve(file);if(!file.endsWith('.js'))file+='.js';if(cache.has(file))return cache.get(file);
  const module={exports:{}};cache.set(file,module.exports);
  vm.runInNewContext(fs.readFileSync(file,'utf8'),{module,wx,Date,Math,Number,Error,Object,Promise,encodeURIComponent,decodeURIComponent,Page:x=>{definition=x;},require:n=>load(path.resolve(path.dirname(file),n))},{filename:file});
  cache.set(file,module.exports);return module.exports;
 }
 const api=load(path.join(root,'services/install.js'));
 async function page(name,q={}){
  definition=null;load(path.join(root,'pages',name,'index.js'));
  const p={...definition,data:JSON.parse(JSON.stringify(definition.data||{})),setData(x){Object.assign(this.data,x);}};
  if(p.onLoad)await p.onLoad(q);if(p.onShow)await p.onShow();return p;
 }
 return {api,page,routes};
}
test('首页到检查、付款、重试、退款的页面操作',async()=>{
 const h=harness(),home=await h.page('home');home.start();assert.equal(h.routes.pop(),'/pages/check/index');
 const check=await h.page('check');await check.demo();await check.next();const id=h.api.load().orders[0].id;
 const checkout=await h.page('checkout',{id});await checkout.pay();assert.equal(h.api.get(id).paymentStatus,'pending');
 checkout.agree({detail:{value:['accepted']}});await checkout.pay();assert.equal(h.api.get(id).paymentStatus,'paid');
 const result=await h.page('result',{id});await result.claim();await result.claim();assert.equal(h.api.get(id).attempts,2);await result.refund();await result.claim();
 assert.equal(h.api.get(id).paymentStatus,'refunded');assert.match(result.data.error,/权益/);
});
test('未通过与未完成页面无法下单',async()=>{
 for(const selected of [1,2]){const h=harness(),p=await h.page('check');p.scenario({detail:{value:String(selected)}});await p.demo();await p.next();assert.equal(h.api.load().orders.length,0);assert.match(p.data.error,/未通过|未完成/);}
});
test('旧通过结果不能遮盖新扫码错误',async()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();
 const p=await h.page('check',{scene:'INVALID-CODE'});
 assert.equal(p.data.check,null);assert.match(p.data.error,/演练只接受/);
});
test('订单取消和未知订单均有正确页面反馈',async()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();const o=h.api.order(),p=await h.page('checkout',{id:o.id});await p.cancel();assert.equal(p.data.order.paymentStatus,'closed');
 const result=await h.page('result',{id:'missing'});assert.equal(result.data.order,null);assert.match(result.data.error,/找不到/);
});
test('有效领取后的刷新清除旧错误提示',async()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();const o=h.api.order();h.api.pay(o.id);
 const p=await h.page('result',{id:o.id});p.setData({error:'旧错误'});await p.refresh();assert.equal(p.data.error,'');
});

test('正式退款页面允许空说明，仍等待服务端状态',async()=>{
 let page;const calls=[];const api={mode:'production',refund:async(id,reason)=>{calls.push({id,reason});},get:async()=>({id:'h1',paymentStatus:'paid',refundStatus:'requested'})};
 const ui={orderView:x=>x,showError:(p,e)=>p.setData({error:e.message})};
 vm.runInNewContext(fs.readFileSync(path.resolve(__dirname,'../pages/result/index.js'),'utf8'),{Page:x=>{page=x;},Promise,require:n=>n.includes('services/install')?api:ui,wx:{showModal:opts=>opts.success({confirm:true})}});
 page.orderId='h1';page.data={...page.data};page.setData=function(x){Object.assign(this.data,x);};
 await page.refund();assert.equal(calls.length,1);assert.equal(calls[0].reason,'');
 assert.equal(page.data.order.paymentStatus,'paid');assert.equal(page.data.order.refundStatus,'requested');
});
