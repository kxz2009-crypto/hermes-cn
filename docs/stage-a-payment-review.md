# 阶段 A：支付复用审阅记录

审阅日期：2026-10-09（北京时间）
审阅对象：企智文献 v1.1.1 小程序与验证后端现网代码（只读审阅，未修改任何线上文件）。
依据：《Hermes_CN_MiniProgram_Paid_Installation_Plan_v1.0.docx》第四节。

## 审阅范围

| 位置 | 文件 | 内容 |
| --- | --- | --- |
| 小程序 | `utils/api.js` | 统一请求封装、401 刷新重放、虚拟支付三接口封装 |
| 小程序 | `config/env.js` | apiBase / sku / 金额（`lit_report_30`，99 元） |
| 小程序 | `pages/order/order.js` | 下单→拉起支付→确认→轮询的完整交互 |
| 后端现网（腾讯） | `src/core/payment/wechat-virtual.ts` | 米大师 xpay 签名、下单参数、query_order 查单 |
| 后端现网（腾讯） | `routes/api/verification/orders.ts` | 下单：幂等键、SKU 白名单、频控、内容安全 |
| 后端现网（腾讯） | `orders/$orderId/virtual-pay-params.ts` / `virtual-pay-confirm.ts` | 拉起参数与支付确认 |
| 后端 | `modules/verification/store.ts` | 订单存储与状态字段 |

## 结论：可复用与须新建

### 可直接复用的模式（不复制业务数据）

1. **签名与查单核心**（`wechat-virtual.ts`）：HMAC-SHA256 生成 `paySig`/`signature`，固定字段顺序的 `signData`；服务端以 `xpay/query_order` 为唯一可信支付来源，status 2–4 才算已支付。逻辑自包含，可按 Provider 契约移植。
2. **fail-closed 原则**：webhook 未接入前，支付确认只走服务端查单；客户端成功提示不作为凭证。新项目沿用。
3. **幂等设计**：`client_idempotency_key` + 请求指纹，重复提交返回 `reuse_existing`；确认接口幂等（非待确认状态直接复用，不重复履约）。
4. **金额校验**：确认时核对实付金额 ≥ 订单金额，不符拒绝交付。
5. **身份桥接**：`wx.login` code → `code2session` → 服务端 session_token（Bearer），生产禁用 dev openid header。新项目照此实现。

### 不可复用、须为新产品新建的部分

1. **商品与账号绑定**：现网 productId=`lit_report_30`、99 元，属旧商品。新产品（9.9 元安装包）须在小程序后台独立创建虚拟支付道具、独立 offerId/appKey 配置，不经客户端传价。
2. **订单模型缺口**：现订单字段无检查会话关联、交付状态、权益快照、领取期限。按方案第四节"订单与交付必须分开"扩展。
3. **履约逻辑**：现履约是生成报告（`triggerOrderReport`）；新项目履约是发放安装权益，须全新实现。
4. **SKU 白名单**：新服务独立配置商品目录，不复用 `ALLOWED_SKUS`。

### 部署边界

现网验证服务运行于腾讯服务器 `/opt/qizhi-literature/apps/web`（3010 端口，systemd）。新项目使用独立服务、独立数据库名与订单命名空间，不修改文献线上商品、不覆盖其存档；`sync-from-vps-lit.sh` 类同步脚本不适用于新项目发布。

## 待确认项（进入阶段 C 前）

- [ ] 新小程序 AppID 与虚拟支付权限开通情况（微信后台道具管理）。
- [ ] 新商品 productId、offerId、现网 AppKey 的申请与配置位置。
- [ ] 领取期限（方案建议 30 天）与退款规则的最终拍板。

## 阶段 A 结论

支付核心模式（签名、查单、幂等、fail-closed、金额校验）成熟可复用；商品、订单模型、履约须新建。阶段 B（免费环境检查）不依赖支付，可先行开发；阶段 C 开工前需补齐上方待确认项。
