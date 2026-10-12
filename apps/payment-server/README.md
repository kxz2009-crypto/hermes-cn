# Hermes CN 虚拟支付服务（候选）

本服务使用独立 SQLite 数据库和 3021 端口，不复用文献产品账号、密钥、数据库或订单。
AppID wx9e5937d752f2125f，OfferID 1450674694，固定道具 hermes_install_990，价格 990 分。

## 当前状态
- 服务端签名、微信登录、查单、身份隔离、订单幂等、退款申请/审核/确认已实现并通过本地测试。
- 小程序 production adapter 已实现，默认仍为 demo；真实微信网络调用、真实金额及退款未测试。
- 私有密钥、正式部署、微信合法 request 域名与消息回调尚未配置或核验。
- 电脑检查会话当前由受信任运营侧 provision-check 建立；公共电脑结果页、二维码生成、安装器消费权益仍待联调。
- 普通模式消息回调会触发服务端查单，不信任消息中的到账/退款字段。AES 安全模式已支持：解密后同样走签名验证+服务端查单，密文解不出来或 receiveid 不匹配时按失败处理，不回 success。配置 HERMES_CALLBACK_AES_KEY（EncodingAESKey，43 位 base64+"="）后启用。
- 领取期限及最终服务条款仍待确认；不要在上述条件未完成时开放客户收费。

## 服务端配置
复制 .env.example 为服务器 /etc/hermes-payments.env。AppSecret、现网 AppKey、运营 token 和回调 token 仅写入该文件，权限 0600。
HERMES_PAYMENT_ENABLED=1 仅在配置与发布条件完成后启用；env=0 使用现网 AppKey，env=1 使用沙箱 AppKey，不混用。
小程序 config/env.js 设置 mode='production'、apiBase='https://hermes.localvram.cn/api/install'、realPaymentEnabled=true 后重新编译。
服务由 hermes-payments.service 启动，监听 127.0.0.1:3021；nginx-location.conf 提供反向代理示例，公网禁止 /admin。
本目录无第三方 Python 依赖；需 Python 3.11+。程序将订单文件权限设为 0600，不记录请求 URL、密钥、session_key 或请求体。

## 订单与退款
前端调用 wx.requestVirtualPayment 时原样传服务端签名；客户端 success 不授予权益。已发起支付的订单不重新签发支付单，先查询原结果；平台关闭后才能新建，避免重复收费。
查单核对业务单号、固定金额和支付状态，再授予一次权益；后台每 5 分钟查未终结订单，支付通知也触发查单。
发货通知在持久化权益后提交，失败重试，不重复授予权益。实际下载/安装仍应由电脑端执行。
退款需要用户最近一次登录态签名；审核时登录已过期需用户重新打开小程序。退款状态 5 仅代表商户侧扣款完成，只有 8 才显示用户已收款；通过退款单号查单。
退款流程：requested（待审核）→ processing（微信任务已提交）→ succeeded（微信确认完成）。
申请/处理中暂停新领取；成功撤销；失败保留已支付订单权益。请求和退款单号幂等，网络超时沿用原退款单查询/重试。
iOS 订单引导 Apple 购买记录申请退款；服务端拒绝对标记为 iOS 的订单主动退款，外部退款查单确认后同样回收权益。
已安装或已下载的软件不能远程回收。

运营侧在服务器加载环境变量后执行：
python3 manage.py approve-refund <订单号>
命令仅批准已经存在的客户退款申请；接口返回处理中不等于资金已经退回。

## 检查关联与电脑同步
受信任运营侧读取 preflight --json 报告，通过：
python3 manage.py provision-check report.json --out session.private.json
生成 code（用于小程序 scene）和 pcToken（电脑端私有 Bearer，不放入二维码或小程序）。
检查通过后扫码进入 pages/check/index；没有小程序内扫一扫按钮。关联码绑定首个微信账号，30 分钟过期。
已支付用户重新完成检查，可复用原安装版本订单并绑定新会话，无需再次付费。
电脑持有 pcToken，通过 GET /pc/checks/<code> 查询订单与 canContinue；退款会关闭 canContinue。
此 API 尚未接到实际电脑页面/安装器，因此不能把本地 API 验证描述为完整交付验收。

## 验证
python3 -m unittest discover -s apps/payment-server -p 'test_*.py' -v
node --test apps/mini-program/tests/*.test.js
微信后台签约与道具配置本身不能替代真实支付、通知、发货和退款联调。

参考：[微信接口](https://developers.weixin.qq.com/miniprogram/dev/api/payment/wx.requestVirtualPayment.html)、
[腾讯 CloudBase 接入参考](https://github.com/TencentCloudBase/skills/blob/main/skills/cloudbase-wechat-integration/references/virtual-payment.md)。
