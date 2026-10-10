const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{scenarios:['检查通过','检查未通过','检查未完成'],selected:0,code:'',check:null,error:''},
onLoad(q){if(q.scene){try{this.setData({code:decodeURIComponent(q.scene)});this.link();}catch(e){this.linkError=true;this.setData({check:null});ui.showError(this,e);}}},
onShow(){if(this.linkError)return;const c=api.load().check;if(c)this.render(c);},
render(c){this.setData({check:c,statusText:({PASS:'通过',BLOCK:'未通过',UNKNOWN:'未完成'})[c.status],expiresText:new Date(c.expiresAt).toLocaleTimeString(),error:''});},
copy(){wx.setClipboardData({data:'https://hermes.localvram.cn'});},input(e){this.setData({code:e.detail.value});},scenario(e){this.setData({selected:Number(e.detail.value)});},
demo(){this.setData({code:['DEMO-PASS','DEMO-BLOCK','DEMO-UNKNOWN'][this.data.selected]});this.link();},
link(){try{const check=api.session(this.data.code.trim());this.linkError=false;this.render(check);}catch(e){this.linkError=true;this.setData({check:null});ui.showError(this,e);}},
scan(){wx.scanCode({onlyFromCamera:true,success:r=>{this.setData({code:r.result||''});this.link();},fail:()=>this.setData({error:'未完成扫码，可重试或输入演练关联码。'})});},
next(){try{api.confirm();const o=api.order();wx.navigateTo({url:'/pages/checkout/index?id='+encodeURIComponent(o.id)});}catch(e){ui.showError(this,e);}}});