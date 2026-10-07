# 安装器保护测试验收

- Commit：`b51e1c6c2b390936cad410c061a54422e35491c6`
- 运行记录：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37684691378

| 平台 / 来源 | 安装器及保护步骤 |
| --- | --- |
| macos-15 / pypi | PASS |
| macos-15 / tuna | PASS |
| macos-15-intel / pypi | PASS |
| macos-15-intel / tuna | PASS |
| ubuntu-24.04 / pypi | PASS |
| ubuntu-24.04 / tuna | PASS |

## 通过项目

- 六组安装器安装与 CLI 启动。
- 六组已有目标目录拒绝覆盖，测试目录内容保持不变。
- Intel 两组错误 wheel 哈希阻断，目标目录未创建。
- 六组启动器帮助命令使用独立配置路径，测试用旧配置保持不变。
- 上游 pyproject.toml 与 uv.lock 未修改。

## 验证边界

配置隔离仅覆盖本次帮助命令测试，不能推广到所有子命令或插件。
尚未验证国内网络完整安装、真实模型对话、可选浏览器功能。
Intel 持久下载接入和再分发声明核查仍待完成。
本记录不是正式发布批准。

