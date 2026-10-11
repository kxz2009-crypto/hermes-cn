const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{mode:api.mode,order:null,agreed:false,busy:false,error:''},
async onLoad(q){this.orderId=q.id||'';await this.refresh();},
async refresh(){try{const o=await api.get(this.orderId);this.setData({order:ui.orderView(o),error:o?'':'订单不存在，请先完成检查。'});}catch(e){ui.showError(this,e);}},
agree(e){this.setData({agreed:e.detail.value.includes('accepted')});},terms(){wx.navigateTo({url:'/pages/terms/index'});},
async pay(){if(!this.data.agreed||this.data.busy)return;this.setData({busy:true,error:''});try{await api.pay(this.orderId);wx.redirectTo({url:'/pages/result/index?id='+encodeURIComponent(this.orderId)});}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});}},
async cancel(){if(this.data.busy)return;this.setData({busy:true});try{await api.cancel(this.orderId);await this.refresh();}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});}},
result(){wx.redirectTo({url:'/pages/result/index?id='+encodeURIComponent(this.orderId)});}});
