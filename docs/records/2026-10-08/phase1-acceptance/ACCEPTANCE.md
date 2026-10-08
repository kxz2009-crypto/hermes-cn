# 一期实验安装入口验收

## 结论

PASS：一期实验安装入口交付范围通过。
本结论不等于生产正式版、中国大陆完整安装链通过，
或完整第三方再分发合规认证。

## 交付对象

- 项目：kxz2009-crypto/hermes-cn。
- 网站：https://hermes.localvram.cn/。
- 页面提交：91d63ca0247d337c13adf62bc73f1b4552cd6232。
- 页面 SHA256：
  4334802eec4349f19f5567159bba0d723d0127d35a9ad97d01e86b305015eff1
- 网站固定安装器版本：a1e57eb。
- Hermes 上游：f97608f178d1ffeca59860195ab7da295f7c8e5f。
- Python：3.11.17；uv：0.12.23。
- Intel 依赖：cryptography 50.0.0 r2 公开实验预发布。

## 通过证据

1. Ubuntu 24.04、macOS 15 ARM、macOS 15 Intel × PyPI/TUNA：
   六组核心依赖、安装器及保护测试通过。
2. Intel 两组不传 --intel-wheel 的自动下载安装通过；
   固定哈希校验及声明、来源文件留存通过。
3. WSL 独立安装、CLI 帮助和版本检查通过。
4. WSL GLM Coding Plan API、Agent 核心调用和 CLI 简短对话
   取得预期回复；具体范围以此前项目记录为准。
5. r2 Release 分发包匿名下载与固定哈希核对通过。
6. 网站通过服务器本机 HTTPS 和 WSL 公网 HTTPS 内容核对。

CI：
https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37724415813

网站部署及公网核对依据为用户提供的终端执行结果。
服务器部署记录：
/srv/localvram/hermes/ops/site-deployments/20261008T040709Z-upload

部署使用 WSL 经 SCP 上传的已校验页面。
未修改 Nginx 配置，未重启或重载服务。
网站保留 noindex,nofollow。

## 已知限制与后续工作

- 腾讯北京节点访问 raw.githubusercontent.com 连续超时。
  页面通过 SCP 完成部署；不能宣称国内完整安装链通过。
- 网页展示的工具自举与安装命令尚未作为完整组合，
  在全新国内环境中执行验收。
- uv 自举和 editable 构建依赖尚未完整哈希锁定。
- 没有验收所有模型、工具、浏览器组件或实体 Mac 模型对话。
- 状态目录隔离不等于操作系统沙箱。
- 第三方声明保留审查范围限制，不是完整链接组件 SBOM。
- 不支持原地升级、复用失败目录或直接搬迁安装目录。
- 原候选测试工作流仍有历史逻辑，后续清理；不要重复触发。
- 页面保留“一期实验预览”及此前未收口措辞，本验收记录
  表示本次交付结论，不扩大网页所述能力范围。

## 后续优先级

先完成一个真实国内环境的网页命令端到端安装，
根据实际失败环节决定镜像或下载策略，再扩展功能和推广范围。
