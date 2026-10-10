
const test=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
function api(mode='demo'){
 let stored;
 const wx={getStorageSync:()=>stored?JSON.parse(JSON.stringify(stored)):undefined,setStorageSync:(k,s)=>{stored=JSON.parse(JSON.stringify(s));}};
 const sandbox={module:{exports:{}},Date,Math,wx,require:name=>name==='../config/env'?{mode}:require('../services/domain')};
 vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../services/install.js'),'utf8'),sandbox);
 return sandbox.module.exports;
}
test('重扫与页面恢复沿用原订单，退款后不可领取',()=>{
 const a=api();const c=a.session('DEMO-PASS');a.confirm();const o=a.order();
 assert.equal(a.session('DEMO-PASS').id,c.id);assert.equal(a.order().id,o.id);
 a.pay(o.id);a.claim(o.id);a.restore(o.id);a.confirm();assert.equal(a.order().id,o.id);
 a.claim(o.id);assert.equal(a.get(o.id).attempts,2);a.refund(o.id);assert.throws(()=>a.claim(o.id),{code:'NO_ENTITLEMENT'});
});
test('真实模式拒绝模拟关联与下单',()=>{const a=api('production');assert.throws(()=>a.session('DEMO-PASS'),{code:'BACKEND_NOT_READY'});assert.throws(()=>a.order(),{code:'BACKEND_NOT_READY'});});
