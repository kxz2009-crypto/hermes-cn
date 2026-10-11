const api=require('../../services/install'),ui=require('../../utils/ui');
Page({data:{mode:api.mode,scenarios:['检查通过','检查未通过','检查未完成'],selected:0,code:'',check:null,error:'',busy:false},
async onLoad(q){if(q.scene){try{this.setData({code:decodeURIComponent(q.scene)});await this.link();}catch(e){this.linkError=true;this.setData({check:null});ui.showError(this,e);}}},
async onShow(){if(this.linkError)return;try{const c=(await api.load()).check;if(c)this.render(c);}catch(e){ui.showError(this,e);}},
render(c){this.setData({check:c,statusText:({PASS:'通过',BLOCK:'未通过',UNKNOWN:'未完成'})[c.status],expiresText:new Date(c.expiresAt).toLocaleTimeString(),error:''});},
copy(){wx.setClipboardData({data:'https://hermes.localvram.cn'});},input(e){this.setData({code:e.detail.value});},scenario(e){this.setData({selected:Number(e.detail.value)});},
async demo(){if(api.mode!=='demo')return;this.setData({code:['DEMO-PASS','DEMO-BLOCK','DEMO-UNKNOWN'][this.data.selected]});await this.link();},
async link(){if(this.data.busy)return;this.setData({busy:true});try{const check=await api.session(this.data.code.trim());this.linkError=false;this.render(check);}catch(e){this.linkError=true;this.setData({check:null});ui.showError(this,e);}finally{this.setData({busy:false});}},
async next(){if(this.data.busy)return;this.setData({busy:true,error:''});try{await api.confirm();const o=await api.order();wx.navigateTo({url:'/pages/checkout/index?id='+encodeURIComponent(o.id)});}catch(e){ui.showError(this,e);}finally{this.setData({busy:false});}}});
