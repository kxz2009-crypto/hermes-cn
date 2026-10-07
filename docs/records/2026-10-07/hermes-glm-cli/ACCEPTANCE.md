# Hermes CLI GLM 简短对话验收

## 判定

PASS：安装器生成的 hermes-cn CLI 完成一次简短模型对话。
原始 result.json 中 REVIEW 保留不改，本文件记录审核结论。

## 证据

- Hermes 上游：f97608f178d1ffeca59860195ab7da295f7c8e5f。
- 安装器提交：f2a862ca4114bad309481a216871c3435d135738。
- 提供商参数：zai。
- 模型：glm-5.3-flash。
- 接口配置：https://open.bigmodel.cn/api/coding/paas/v4。
- CLI 退出码：0。
- 实际回复：HERMES_CLI_GLM_OK。
- 耗时：26.5 秒。
- 运行参数：safe-mode、oneshot、quiet、max-turns=1、run-budget=60。
- 密钥通过子进程环境传入，没有写入归档或命令参数。

## 已知提示

tirith security scanner enabled but not available。
运行时提示命令扫描退回模式匹配。
本次不验收 tirith 或完整命令扫描能力。

## 验证边界

本次验证 WSL 独立安装的 CLI 简短对话。
安全模式不代表全部内置工具关闭；未验收工具隔离或工具执行。
接口地址是请求配置值，本次没有独立网络抓包核验。
未验证腾讯北京完整安装、长任务、浏览器、其他可选组件。
不据此宣布公开发行就绪。
