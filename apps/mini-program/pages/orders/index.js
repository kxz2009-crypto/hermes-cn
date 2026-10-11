const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{mode:api.mode,orders:[],error:''},
async onShow(){try{const s=await api.load();this.setData({orders:s.orders.map(ui.orderView),error:''});}catch(e){ui.showError(this,e);}},
open(e){wx.navigateTo({url:'/pages/result/index?id='+encodeURIComponent(e.currentTarget.dataset.id)});},
async restore(e){try{await api.restore(e.currentTarget.dataset.id);wx.navigateTo({url:'/pages/check/index'});}catch(x){ui.showError(this,x);}},
check(){wx.navigateTo({url:'/pages/check/index'});}});
