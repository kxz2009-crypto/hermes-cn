
const RULE_VERSION='miniapp-demo-v1';
const PRODUCT=Object.freeze({id:'hermes_install_990',name:'Hermes CN 办公助手自助安装包',priceFen:990,version:'3861473',rulesVersion:'draft-v1',claimDays:null});
function error(code,message){const e=new Error(message);e.code=code;return e;}
function validateCheck(c,now){
 if(!c||c.status!=='PASS')throw error('CHECK_NOT_PASS','电脑检查未通过或尚未完成，请先重新检查。');
 if(c.ruleVersion!==RULE_VERSION)throw error('CHECK_RULE_CHANGED','检查规则已更新，请重新检查。');
 if(c.productVersion!==PRODUCT.version)throw error('CHECK_VERSION_CHANGED','安装版本已变化，请重新检查。');
 if(!Number.isFinite(c.expiresAt)||c.expiresAt<=now)throw error('CHECK_EXPIRED','检查结果已过期，请重新检查。');
 if(!c.confirmed)throw error('LINK_UNCONFIRMED','请先确认关联的电脑检查结果。');
}
function createOrder(s,now,id){
 validateCheck(s.check,now);
 const old=s.orders.find(o=>o.checkId===s.check.id&&['pending','paid'].includes(o.paymentStatus));
 if(old)return old;
 const o={id,checkId:s.check.id,product:{...PRODUCT},paymentStatus:'pending',deliveryStatus:'waiting',createdAt:now,attempts:0};s.orders.unshift(o);return o;
}
function completeDemoPayment(s,id,now){
 const o=s.orders.find(o=>o.id===id);if(!o)throw error('ORDER_NOT_FOUND','找不到演练订单。');
 if(o.paymentStatus==='paid')return o;
 if(o.paymentStatus!=='pending')throw error('ORDER_CLOSED','订单已关闭。');
 validateCheck(s.check,now);if(o.checkId!==s.check.id)throw error('CHECK_MISMATCH','检查会话与订单不一致。');
 o.paymentStatus='paid';o.deliveryStatus='available';return o;
}
function demoClaim(s,id,now){
 const o=s.orders.find(x=>x.id===id);if(!o||o.paymentStatus!=='paid'||o.deliveryStatus==='revoked')throw error('NO_ENTITLEMENT','订单尚无可领取权益。');
 validateCheck(s.check,now);if(o.checkId!==s.check.id)throw error('CHECK_MISMATCH','请重新关联原订单后继续安装。');
 o.attempts+=1;return o;
}
module.exports={RULE_VERSION,PRODUCT,error,validateCheck,createOrder,completeDemoPayment,demoClaim};
