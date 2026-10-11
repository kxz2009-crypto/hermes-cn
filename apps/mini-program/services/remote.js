const env=require('../config/env'),product=require('./domain').PRODUCT;
let token='',check=null,loginTask=null;
function error(code,message){const e=new Error(message);e.code=code;return e;}
function raw(path,method,data,bearer){
 return new Promise((resolve,reject)=>{
  if(!/^https:\/\//.test(env.apiBase))return reject(error('BACKEND_NOT_READY','支付服务地址尚未配置。'));
  wx.request({url:env.apiBase.replace(/\/$/,'')+path,method,data,timeout:15000,
   header:{'Content-Type':'application/json',...(bearer?{Authorization:'Bearer '+bearer}:{})},
   success:r=>{if(r.statusCode>=200&&r.statusCode<300)resolve(r.data);else reject(error(r.data&&r.data.code||'REQUEST_FAILED',r.data&&r.data.message||'订单服务暂不可用。'));},
   fail:()=>reject(error('NETWORK_ERROR','连接失败，请稍后查询原订单；不要重复购买。'))});
 });
}
function login(force=false){
 if(token&&!force)return Promise.resolve();
 if(loginTask)return loginTask;
 loginTask=new Promise((resolve,reject)=>wx.login({success:r=>r.code?resolve(r.code):reject(error('LOGIN_FAILED','微信登录失败。')),fail:()=>reject(error('LOGIN_FAILED','微信登录失败。'))}))
 .then(code=>raw('/auth/login','POST',{code})).then(r=>{token=r.token;}).finally(()=>{loginTask=null;});
 return loginTask;
}
async function request(path,method='GET',data){
 await login();
 try{return await raw(path,method,data,token);}
 catch(e){if(e.code!=='LOGIN_EXPIRED')throw e;token='';await login();return raw(path,method,data,token);}
}
function orderPath(id,action=''){return '/orders/'+encodeURIComponent(id)+(action?'/'+action:'');}
function platform(){try{return wx.getSystemInfoSync().platform;}catch(e){return 'unknown';}}
async function session(code){check=null;check=await request('/checks/link','POST',{code});return check;}
async function confirm(){if(!check)throw error('CHECK_NOT_FOUND','请先关联电脑检查。');check=await request('/checks/confirm','POST',{checkId:check.id});return check;}
async function order(){if(!check)throw error('CHECK_NOT_FOUND','请先关联电脑检查。');return request('/orders','POST',{checkId:check.id,platform:platform()});}
async function pay(id){
 if(!env.realPaymentEnabled)throw error('PAYMENT_DISABLED','真实支付尚未启用。');
 if(typeof wx.requestVirtualPayment!=='function'||(wx.canIUse&&!wx.canIUse('requestVirtualPayment')))throw error('PAYMENT_UNSUPPORTED','当前微信版本不支持虚拟支付，请更新微信。');
 // Refresh login immediately before signing, and pass signData through byte-for-byte.
 await login(true);
 const p=await request(orderPath(id,'pay-params'),'POST',{});
 if(p.mode!=='short_series_goods'||typeof p.signData!=='string'||!p.paySig||!p.signature)throw error('PAYMENT_PARAMS','支付参数不完整，请稍后查询原订单。');
 let failure;
 try{await new Promise((resolve,reject)=>wx.requestVirtualPayment({mode:p.mode,signData:p.signData,paySig:p.paySig,signature:p.signature,success:resolve,fail:reject}));}
 catch(e){failure=e;}
 // A timeout/cancel can race a successful payment: query before displaying failure.
 let current=await request(orderPath(id,'confirm'),'POST',{});
 if(current.paymentStatus==='paid'||current.paymentStatus==='refunded')return current;
 if(failure){
  if(/cancel/i.test(failure.errMsg||''))throw error('PAYMENT_CANCELLED','已取消付款，请在我的订单查询原订单状态。');
  throw error('PAYMENT_UNCONFIRMED','支付结果尚未确认，请在我的订单查询，不要重复购买。');
 }
 for(let n=0;n<4&&current.paymentStatus==='pending';n++){
  await new Promise(resolve=>setTimeout(resolve,1500));
  current=await request(orderPath(id,'confirm'),'POST',{});
 }
 // Pending remains pending. Result page explains reconciliation instead of inventing success.
 return current;
}
module.exports={mode:'production',product,session,confirm,order,pay,
 get:id=>request(orderPath(id)),cancel:id=>request(orderPath(id,'cancel'),'POST',{}),
 claim:id=>request(orderPath(id,'continue'),'POST',{}),
 async refund(id,reason){await login(true);return request(orderPath(id,'refund'),'POST',{reason});},
 async load(){return {check,orders:await request('/orders')};},
 async restore(id){const o=await request(orderPath(id));if(o.paymentStatus!=='paid')throw error('RESTORE_UNAVAILABLE','请先查看订单状态。');return o;},
 request,login};
