
const env=require('../config/env'),d=require('./domain'),KEY='hermes_cn_demo_v1';
function load(){const s=wx.getStorageSync(KEY);return s&&Array.isArray(s.orders)?s:{check:null,orders:[]};}
function save(s){wx.setStorageSync(KEY,s);}
function demoOnly(){if(env.mode!=='demo')throw d.error('BACKEND_NOT_READY','真实服务尚未接入，暂不能关联、下单或领取。');}
function id(p){return p+'_'+Date.now().toString(36)+'_'+Math.random().toString(36).slice(2,10);}
function session(code){
 demoOnly();if(!/^DEMO-(PASS|BLOCK|UNKNOWN)$/.test(code))throw d.error('INVALID_LINK','演练只接受 DEMO-PASS、DEMO-BLOCK 或 DEMO-UNKNOWN。真实关联需后台接入。');
 const now=Date.now(),s=load();
 if(s.check && s.check.code===code && s.check.expiresAt>now)return s.check;
 s.check={id:id('check'),status:code.slice(5),ruleVersion:d.RULE_VERSION,productVersion:d.PRODUCT.version,checkedAt:now,expiresAt:now+30*60000,confirmed:false,environment:'Windows / WSL2 · 演练示例',code};save(s);return s.check;
}
function confirm(){demoOnly();const s=load();if(!s.check)throw new Error('请先取得检查结果。');s.check.confirmed=true;save(s);return s.check;}
function order(){demoOnly();const s=load(),o=d.createOrder(s,Date.now(),id('demo'));save(s);return o;}
function pay(i){demoOnly();const s=load(),o=d.completeDemoPayment(s,i,Date.now());save(s);return o;}
function cancel(i){demoOnly();const s=load(),o=s.orders.find(x=>x.id===i);if(o&&o.paymentStatus==='pending')o.paymentStatus='closed';save(s);}
function claim(i){demoOnly();const s=load(),o=d.demoClaim(s,i,Date.now());save(s);return o;}
function refund(i){demoOnly();const s=load(),o=s.orders.find(x=>x.id===i);if(!o||o.paymentStatus!=='paid')throw new Error('订单不支持演练退款。');o.paymentStatus='refunded';o.deliveryStatus='revoked';save(s);return o;}
function get(i){return load().orders.find(x=>x.id===i)||null;}
function restore(i){demoOnly();const s=load(),o=s.orders.find(x=>x.id===i);if(!o||!['pending','paid'].includes(o.paymentStatus))throw new Error('订单不能恢复。');s.check={id:o.checkId,status:'PASS',ruleVersion:d.RULE_VERSION,productVersion:o.product.version,checkedAt:Date.now(),expiresAt:Date.now()+30*60000,confirmed:false,environment:'原订单电脑 · 恢复演练'};save(s);return s.check;}
module.exports={session,confirm,order,pay,cancel,claim,refund,get,restore,load,product:d.PRODUCT,mode:env.mode};
