const env=require('../config/env');
function showError(p,e){p.setData({error:(e&&e.message)||'操作失败，请重试。'});}
function orderView(o){if(!o)return null;const demo=env.mode==='demo';return {...o,
 price:(o.product.priceFen/100).toFixed(2),
 paymentText:({pending:'待确认支付',paid:demo?'演练已支付':'已支付',closed:'已关闭',refunded:demo?'演练已退款':'已退款'})[o.paymentStatus]||'未知',
 refundText:({none:'',requested:'退款申请待审核',processing:'平台退款处理中',succeeded:'退款已成功',failed:'退款未成功，可重新申请'})[o.refundStatus||'none']||'',
 deliveryText:({waiting:'待发放',available:demo?'演练可领取':'可回电脑继续安装',held:'退款处理中，暂停领取',revoked:'权益已撤销'})[o.deliveryStatus]||'未知',
 canClaim:o.paymentStatus==='paid'&&['none','failed'].includes(o.refundStatus||'none')&&o.deliveryStatus!=='revoked',
 canRefund:o.paymentStatus==='paid'&&['none','failed'].includes(o.refundStatus||'none'),
 time:new Date(o.createdAt).toLocaleString()};}
module.exports={showError,orderView};
