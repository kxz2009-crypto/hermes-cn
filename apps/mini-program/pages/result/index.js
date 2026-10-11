const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{mode:api.mode,order:null,error:'',claimMessage:'',busy:false,refundReason:''},
async onLoad(q){this.orderId=q.id||'';await this.refresh();},
async refresh(){try{const o=await api.get(this.orderId);this.setData({order:ui.orderView(o),error:o?'':'找不到订单，请从我的订单重新打开。'});}catch(e){ui.showError(this,e);}},
reason(e){this.setData({refundReason:e.detail.value});},
async claim(){if(this.data.busy)return;this.setData({busy:true});try{const r=await api.claim(this.orderId);this.setData({error:'',claimMessage:api.mode==='demo'?'演练领取成功，尝试 '+r.attempts+' 次；没有下载或安装软件。':r.message});await this.refresh();}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});}},
refund(){if(this.data.busy)return;const demo=api.mode==='demo';
 if(!demo&&!(this.data.refundReason||'').trim()){this.setData({error:'请填写退款原因。'});return;}
 return new Promise(resolve=>wx.showModal({title:demo?'演练退款':'申请退款',content:demo?'撤销模拟订单领取资格，不发生真实资金变动。':'提交后等待审核及平台处理，退款成功后撤销领取权益。已安装软件无法远程收回。',
 success:async r=>{if(!r.confirm||this.data.busy){resolve();return;}this.setData({busy:true,error:''});try{await api.refund(this.orderId,this.data.refundReason);this.setData({claimMessage:''});await this.refresh();}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});resolve();}},fail:()=>resolve()}));},
appleRefund(){wx.showModal({title:'Apple 订单退款',content:'请前往 Apple 购买记录或 reportaproblem.apple.com 申请退款。结果由 Apple 处理，订单状态会在确认后更新。',showCancel:false});},
checkout(){wx.redirectTo({url:'/pages/checkout/index?id='+encodeURIComponent(this.orderId)});},
orders(){wx.navigateTo({url:'/pages/orders/index'});},help(){wx.navigateTo({url:'/pages/help/index'});}});
