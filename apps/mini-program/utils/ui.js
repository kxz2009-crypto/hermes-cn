
function showError(p,e){p.setData({error:(e&&e.message)||'操作失败，请重试。'});}
function orderView(o){if(!o)return null;return {...o,price:(o.product.priceFen/100).toFixed(2),paymentText:({pending:'待支付',paid:'演练已支付',closed:'已关闭',refunded:'演练已退款'})[o.paymentStatus]||'未知',deliveryText:({waiting:'待发放',available:'演练可领取',revoked:'权益已撤销'})[o.deliveryStatus]||'未知',time:new Date(o.createdAt).toLocaleString()};}
module.exports={showError,orderView};
