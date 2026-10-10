
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
 function page(name,q={}){
  definition=null;load(path.join(root,'pages',name,'index.js'));
  const p={...definition,data:JSON.parse(JSON.stringify(definition.data||{})),setData(x){Object.assign(this.data,x);}};
  if(p.onLoad)p.onLoad(q);if(p.onShow)p.onShow();return p;
 }
 return {api,page,routes};
}
test('首页到检查、付款、重试、退款的页面操作',()=>{
 const h=harness(),home=h.page('home');home.start();assert.equal(h.routes.pop(),'/pages/check/index');
 const check=h.page('check');check.demo();check.next();const id=h.api.load().orders[0].id;
 const checkout=h.page('checkout',{id});checkout.pay();assert.equal(h.api.get(id).paymentStatus,'pending');
 checkout.agree({detail:{value:['accepted']}});checkout.pay();assert.equal(h.api.get(id).paymentStatus,'paid');
 const result=h.page('result',{id});result.claim();result.claim();assert.equal(h.api.get(id).attempts,2);result.refund();result.claim();
 assert.equal(h.api.get(id).paymentStatus,'refunded');assert.match(result.data.error,/权益/);
});
test('未通过与未完成页面无法下单',()=>{
 for(const selected of [1,2]){const h=harness(),p=h.page('check');p.scenario({detail:{value:String(selected)}});p.demo();p.next();assert.equal(h.api.load().orders.length,0);assert.match(p.data.error,/未通过|未完成/);}
});
test('旧通过结果不能遮盖新扫码错误',()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();
 const p=h.page('check',{scene:'INVALID-CODE'});
 assert.equal(p.data.check,null);assert.match(p.data.error,/演练只接受/);
});
test('订单取消和未知订单均有正确页面反馈',()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();const o=h.api.order(),p=h.page('checkout',{id:o.id});p.cancel();assert.equal(p.data.order.paymentStatus,'closed');
 const result=h.page('result',{id:'missing'});assert.equal(result.data.order,null);assert.match(result.data.error,/找不到/);
});
test('有效领取后的刷新清除旧错误提示',()=>{
 const h=harness();h.api.session('DEMO-PASS');h.api.confirm();const o=h.api.order();h.api.pay(o.id);
 const p=h.page('result',{id:o.id});p.setData({error:'旧错误'});p.refresh();assert.equal(p.data.error,'');
});
