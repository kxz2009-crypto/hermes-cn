# Phase 2 · 阶段 A 基线审计报告

审计日期：2026-10-09（北京时间）
审计人：Hermes（接替 ChatGPT 继续 Phase 2）
审计方式：只读取证；线上仅本机连通性探测，未修改任何生产文件。

## 审计范围与证据

### 1. 本地仓库

- 路径：`/home/gao20/projects/hermes-cn`，分支 main，工作树干净。
- HEAD：`02f3205`（含 241b3d9 免责声明修订、55d9d5d 视频占位+限额候选、602d706 支付审阅）。
- 远端：`https://github.com/kxz2009-crypto/hermes-cn.git`，与 origin/main 同步。

### 2. CI（GitHub Actions）

- 最近运行：Platform environment check 全部 ok（02f3205、55d9d5d）。
- 工作流五个：platform-check、core-deps-probe、intel-candidate-probe、
  intel-crypto-wheel、draft-asset-access。
- 最近一次 core-deps-probe：run 37827091899（ok）。

### 3. 线上站点（公网回读 + 服务器本机核对）

- 五个静态资源齐备：index/guide/install-assistant.html、product.css/js。
- 备案文字：京ICP备2026009936号 · 京公网安备11010802047815号。
- 免责声明句已按用户要求移除（2026-10-09 部署记录
  20261009T194227Z-241b3d9.W61HNnyA）。
- robots.txt 存在；视频占位区块仅入仓库未部署（等待素材）。

### 4. 固定安装器

- 标识：`386147344dee20b2921da4afb40c188d6beda499`（目录名）。
- 服务器文件（`/srv/localvram/hermes/public/downloads/installers/…`）：
  ```
  b2c33b64e812ca0b1c52ecff096235a8c4f82d5c753c76119538e07e5f0adebc  SHA256SUMS
  d0fa4335b95f59ca8fb87adbabcfa39ef634716df3a9652dbee07ad84fee06b5  SOURCE.txt
  8315f40752f0149e5e1d8b97f3926153d49a16189f3f362c047b559ca35152d7  install-lite.sh
  ```
- 源码内嵌校验与保护测试：`scripts/install-lite.sh`（1074 行，
  含既有安装检测、模型配置保护、错误分类）。

### 5. 问答后端（安装助手 API）

- 服务：`hermes-install-assistant.service`（active，gunicorn
  127.0.0.1:3016，双 worker，sync，timeout=40）。
- 独立用户 `hermes-web-assistant`，systemd 加固
  （ProtectSystem=strict、PrivateTmp、MemoryMax=512M 等）。
- 三层结构：assistant_app（校验/凭据脱敏/模型调用）→
  guarded_app（X-Real-IP 门控）→ quota（SQLite 限额）。
- 限额已按 2026-10-09 需求实装并实测（每分钟3/每地址日20/
  全站日100/并发2、北京时间切日、HMAC 不可还原标识、重启不清零）。
- Nginx：`location = /api/install-assistant/chat` 仅 allow 127.0.0.1/::1
  且 proxy_set_header X-Real-IP $remote_addr → 公网 POST 返回 403。
- 模型密钥：service.env 中（本审计只看键名未读值）。
- 开机自启：**disabled**（有意为之，试运行阶段）。

### 6. 平台测试覆盖

- 六组 CI 验证：Ubuntu 24.04、macOS 15 ARM、macOS 15 Intel ×
  PyPI/TUNA（docs/records/2026-10-08/phase1-acceptance）。
- 真实设备：另一台 Windows/WSL 无代理完整安装 + DeepSeek 实测
  （mainland-fresh-install/ACCEPTANCE.md，用户提供确认，非远程代执行）。

### 7. 部署与回滚

- 部署路径：`/srv/localvram/hermes/public`（静态）+
  `/srv/localvram/hermes/assistant-api`（问答后端）。
- 磁盘：vda1 40G 用 47%（余 22G）。
- 部署留痕：`/srv/localvram/hermes/ops/site-deployments/`（每次含
  before 备份、SHA256SUMS、ACCEPTANCE、自动回滚 trap）。
- 发布方法：仓库核对→打包→上传→服务器备份→原子替换→本机
  HTTPS 哈希校验→公网回读校验；失败自动恢复旧文件。

## 三类事实清单

### A. 有真实证据证明已完成

1. 五个静态页面部署与校验流程（含本次页脚修订）。
2. 固定安装器 3861473 发布与 SHA256 留痕。
3. 六组跨平台 CI + 一台 Windows/WSL 真实安装/DeepSeek 对话。
4. 问答后端三层防护（凭据脱敏/来源门控/限额）运行中且实测通过。
5. 部署记录与回滚机制（ops/site-deployments 留痕完整）。
6. 阶段支付复用审阅（docs/stage-a-payment-review.md，602d706）。

### B. 有代码/配置，尚未充分验证

1. 问答限额：生产实测只覆盖每分钟桶（429 实测）与缩小额度模拟；
   全站 100/日、并发 2 的生产真实压力未演练（离线单测已覆盖）。
2. GLM 入口（hermes-glm）：离线检查过，真实服务器对话曾 429 未通过。
3. install-assistant 前端 UI 预览：与后端真实问答的联调验收未做。
4. 视频演示区块：占位已入仓库，视频素材与部署未完成。

### C. 尚未开发或无法确认

1. preflight 自动环境检测器（阶段 B 本体）——未开发。
2. 安装/恢复机制与安装器的集成（阶段 C 的检测前置）——未开发。
3. 小程序、订单、支付、交付后台——仅完成支付模式审阅，未开发。
4. Mac（两种芯片）真实设备复测——无本机，无法确认。
5. 上游合规/品牌使用的正式核对——未做。

## 进入阶段 B 的条件

满足：仓库干净、CI 绿、部署回滚机制完备、限额防护已实装、
阶段 A 报告落盘。阶段 B（preflight 检测器）为纯新增模块，
不影响线上静态页与安装器，可在仓库内独立开发+离线测试。

**裁定：ACCEPTED**（阶段 A 通过，可进入阶段 B）
