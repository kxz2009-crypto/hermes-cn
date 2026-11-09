const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{mode:api.mode,order:null,error:'',claimMessage:'',busy:false,refundReason:''},
async onLoad(q){this.orderId=q.id||'';await this.refresh();},
async refresh(){try{const o=await api.get(this.orderId);this.setData({order:ui.orderView(o),error:o?'':'找不到订单，请从我的订单重新打开。'});}catch(e){ui.showError(this,e);}},
reason(e){this.setData({refundReason:e.detail.value});},
async claim(){if(this.data.busy)return;this.setData({busy:true});try{const r=await api.claim(this.orderId);this.setData({error:'',claimMessage:api.mode==='demo'?'演练领取成功，尝试 '+r.attempts+' 次；没有下载或安装软件。':r.message});await this.refresh();}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});}},
refund(){if(this.data.busy)return;const demo=api.mode==='demo';
 return new Promise(resolve=>wx.showModal({title:demo?'演练退款':'申请退款',content:demo?'撤销模拟订单领取资格，不发生真实资金变动。':'安装完成并有效验收前可申请全额退款。安装验收后，依法享有的售后救济仍保留。退款说明可不填写。提交后等待平台确认，不把申请当作退款成功。付款、下载或安装进程结束不等于有效验收。退款成功仅撤销本订单已提供的在线权益，不影响 Hermes 开源许可证，不删除用户数据；如持有已签发的有效离线凭证，不能承诺实时撤销。',
 success:async r=>{if(!r.confirm||this.data.busy){resolve();return;}this.setData({busy:true,error:''});try{await api.refund(this.orderId,this.data.refundReason);this.setData({claimMessage:''});await this.refresh();}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});resolve();}},fail:()=>resolve()}));},
appleRefund(){wx.showModal({title:'Apple 订单退款',content:'请前往 Apple 购买记录或 reportaproblem.apple.com 申请退款。结果由 Apple 处理，订单状态会在确认后更新。',showCancel:false});},
checkout(){wx.redirectTo({url:'/pages/checkout/index?id='+encodeURIComponent(this.orderId)});},
orders(){wx.navigateTo({url:'/pages/orders/index'});},help(){wx.navigateTo({url:'/pages/help/index'});}});
