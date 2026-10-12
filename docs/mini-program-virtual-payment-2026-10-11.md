# Hermes CN 虚拟支付接入记录 · 2026-10-11

状态：候选代码已完成本地验证，真实收费未启用，服务端未部署。
商品：hermes_install_990；名称：Hermes CN 自助安装包；价格 990 分。
AppID：wx9e5937d752f2125f；OfferID：1450674694。

## 已实现
- 独立 Python/SQLite 订单服务；微信登录与 Bearer 身份；session_key 只在内存，不写入订单。
- 按固定商品和金额计算 paySig/signature；小程序调用 wx.requestVirtualPayment 后查服务端确认。
- 支付单与账号、电脑检查关联；重复订单复用，已发起支付先查询，避免重复收费。
- 已付用户重新完成检查可恢复原版本订单。
- 退款申请、运营审核、退款双签名、退款单查询与状态同步。
- 按官方状态枚举：5 只代表商户侧扣款完成，8 才表示用户收款完成。
- 退款通知按 MchOrderId/MchRefundId 对应原支付与退款单；核对 OpenId，不把 FromUserName 当用户。
- JSON/XML 普通模式回调核验后再查微信；后台每 5 分钟对账；发货持久化、重试不重复授予权益。
- iOS 按 Apple 退款流程处理，服务端据 order_type=7 识别 Apple 订单。
- 电脑会话查询返回 canContinue；申请/处理中暂停新领取，成功撤销，失败保留已付权益。
- 去掉小程序内扫码按钮；先电脑检查，再退出小程序用微信扫一扫进入，付款后回电脑继续。
- 前端接入异步 production adapter，保留默认 demo 和关闭的真实支付开关。
- AES 安全模式回调（2026-10-12）：纯标准库 AES-256-CBC 解密（FIPS-197 KAT 验证）+ 官方 16B随机/4B长度/密文/receiveid 格式核验；解密后仍走签名验证+服务端查单，解不出来或 receiveid 不匹配一律失败关闭、不回 success。配置 HERMES_CALLBACK_AES_KEY（EncodingAESKey 43 位 base64）启用，未配置收到 aes 回调返回 503。

## 验证
- 43 项服务端测试全部通过：包含实际本地 HTTP 路由与模拟微信上游。
- 18 项小程序 Node 测试全部通过。
- 官方文档提供的 pay_sig 与用户态 signature 已与固定测试向量核对。
- 七页 WXML / WXSS 原生编译通过，退出码 0，无 stderr。
- 开发者工具实际模拟器 16 项演练检查通过，exception/console error 均为空。
- 模拟器覆盖演练退款后拦截领取；真实 API adapter 的微信支付回调在单测中模拟。
- 以上不代表真实微信支付、真机退款、生产压力或完整电脑安装交付已验收。
- 代理环境的等待时间不据此认定为小程序性能问题；用户已反馈国内环境实测很快。

## 待完成
1. 服务器配置 AppSecret、现网 AppKey、运营 token、回调 token 与 AES key（HERMES_CALLBACK_AES_KEY，如后台启用安全模式）；发布独立服务与 HTTPS 路由。
2. 微信 request 合法域名、商品现网发布及消息推送配置。
3. 公共电脑结果页/二维码与安装器消费权益联调。当前仅有受信任运营侧检查会话及电脑状态 API。
4. 最终服务范围、领取期限与退款规则公布；当前这些规则仍为草案。
5. 用户授权后进行真机真实支付与退款试单、后台账单核对。

## 配置
密钥空文件已在开发机 work/hermes-payment-secrets.env 生成，未读取或展示密钥值。
Chrome 控制工具因 sandboxCwd 本地 URI 兼容错误未能启动。请在本机填入，不粘贴到聊天。
完整服务配置及运营步骤见 apps/payment-server/README.md。
