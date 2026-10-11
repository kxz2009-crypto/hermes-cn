const api=require('../../services/install');
Page({data:{mode:api.mode},start(){wx.navigateTo({url:'/pages/check/index'});},orders(){wx.navigateTo({url:'/pages/orders/index'});},help(){wx.navigateTo({url:'/pages/help/index'});},terms(){wx.navigateTo({url:'/pages/terms/index'});}});
