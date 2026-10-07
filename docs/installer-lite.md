# 实验轻量安装器

状态：实验版，未批准公开发行。

此前安装器及保护测试在 Ubuntu 24.04、macOS 15 arm64、
macOS 15 x86_64 与 PyPI/TUNA 六组组合中通过。
本次增加 Python 安装的 --no-bin，修改后的 CI 结果待核实。

## 参数与前提

- --prefix：不存在的绝对路径；不支持含空白的路径。
- --uv：uv 0.12.23 可执行文件的绝对路径。
- --source：tuna（默认）或 pypi。
- --intel-wheel：Intel Mac 必须提供已验证的本地 wheel。

当前平台范围：
- Linux x86_64；CI 验证发行版为 Ubuntu 24.04。
- macOS 15 arm64、x86_64；其他 macOS 版本暂拒绝安装。

## 行为

固定 Hermes commit 与 Python 3.11.17，导出上游锁定核心依赖。
Python 安装使用 --no-bin，禁止该步骤向默认 bin 安装命令链接。
运行依赖要求 wheel 与哈希校验；Intel 单独替换 cryptography 来源。
本体采用 editable 安装，构建依赖版本约束但尚未完整哈希锁定。
安装目录内提供 bin/hermes-cn，默认 HERMES_HOME 为该目录的 state。
不添加全局 PATH、不运行 setup、不安装后台服务。
失败时保留现场；成功后生成 INSTALL_COMPLETE 标记。
不支持原地升级、自动修复和失败重试复用目录。
虚拟环境与 editable 路径绑定，安装目录不能直接搬迁。

## 已有验证与限制

六组已有目标目录拒绝覆盖测试通过。
Intel 两组错误 wheel 哈希阻断测试通过。
配置隔离测试仅覆盖帮助命令，不代表所有子命令或插件。

WSL 独立工具环境通过 TUNA 下载并安装 uv 0.12.23，
现用 uv 0.10.9 保持不变；这不是腾讯北京网络测试。

尚未验证国内完整安装、模型对话、浏览器及可选工具。
Git 源码和 Python 下载仍依赖上游服务。
本脚本不限制启动后的所有网络访问或用户主动执行的上游子命令。
发布前仍需完成许可证核查和持久资产分发。
CI 的 Intel wheel 仍使用临时 Actions 产物。
