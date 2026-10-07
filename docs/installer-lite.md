# 实验轻量安装器

状态：待本次 CI 验证，不是公开发行版。

入口：scripts/install-lite.sh

## 参数与前提

- --prefix：必须为不存在的绝对路径；当前不支持含空白的路径。
- --uv：uv 0.12.23 可执行文件的绝对路径。
- --source：tuna（默认）或 pypi。
- --intel-wheel：Intel Mac 必须提供已验证的本地 wheel。

当前平台范围：
- Linux x86_64；CI 验证发行版为 Ubuntu 24.04。
- macOS 15 arm64、x86_64；其他 macOS 版本暂拒绝安装。

## 行为

固定 Hermes commit 与 Python 3.11.17，导出上游锁定核心依赖。
运行依赖要求 wheel 与哈希校验；Intel 单独替换 cryptography 来源。
本体采用 editable 安装，构建依赖版本约束但尚未完整哈希锁定。
安装目录内提供 bin/hermes-cn，默认 HERMES_HOME 为该目录的 state。
不添加全局 PATH、不运行 setup、不安装后台服务。
失败时保留现场；安装成功后生成 INSTALL_COMPLETE 标记。
目前不支持原地升级、自动修复和失败重试复用目录。
虚拟环境与 editable 路径绑定，安装目录不能直接搬迁。

## 尚未覆盖

uv 自举、国内完整下载链、模型对话、浏览器及可选工具。
Git 源码和 Python 下载仍依赖上游服务。
本脚本不限制启动后的所有网络访问或用户主动执行的上游子命令。
发布前还需补齐许可证核查、持久资产分发和隔离行为测试。
