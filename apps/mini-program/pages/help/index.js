Page({data:{items:[
{code:'NETWORK',title:'下载失败或超时',action:'确认电脑网络并检查下载源，包校验通过前不要执行安装。'},
{code:'DISK',title:'磁盘空间不足',action:'确认目标磁盘可用空间；完成准备后重新检查。'},
{code:'DIRECTORY',title:'已有安装或目录冲突',action:'保留原目录和配置，不要直接删除 .hermes 来重试。'},
{code:'PERMISSION',title:'目录不可写',action:'使用有权限的目标目录并重新检测，不盲目使用管理员权限。'},
{code:'MODEL_AUTH',title:'模型认证或额度错误',action:'在电脑本地核对服务商、模型、密钥和额度，不需要重新购买安装包。'},
{code:'ORDER_SYNC',title:'付款后电脑未更新',action:'查询原订单并恢复关联，不要重复付款。演练可从我的订单恢复。'}]},copy(){wx.setClipboardData({data:'https://hermes.localvram.cn/guide.html'});}});