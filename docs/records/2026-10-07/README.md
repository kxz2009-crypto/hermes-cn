# Hermes CN 阶段记录：2026-10-07

## 版本基线

- 项目仓库：kxz2009-crypto/hermes-cn
- CLI 测试提交：0bbe4fd357a0b6ade2554bdf0849060eeda0c98e
- 上游：NousResearch/hermes-agent
- 上游发布标签：v2026.9.24
- 上游 commit：f97608f178d1ffeca59860195ab7da295f7c8e5f
- Hermes 包版本：0.21.5
- 测试 Python：3.11.17

## 验证结果

Ubuntu 24.04 x86_64、macOS 15 Apple Silicon、macOS 15 Intel，
各搭配 PyPI、TUNA，共六组，以下检查全部通过：

- 核心依赖预编译包安装与哈希校验。
- cryptography 加密、解密和签名验证。
- Hermes 源码 editable 安装。
- hermes --help、hermes --version 启动。
- 上游 pyproject.toml 和 uv.lock 未修改。

证据：
- 核心依赖：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37680437611
- 本体与 CLI：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37681372930
- Intel wheel：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37679350161

## Intel 自建依赖

文件：cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl

SHA256：
bb6320d4dc523339041c40e58176beb3235d59c133968490694fd1924c68c49c

大小：3838299 字节。

静态链接 OpenSSL 3.6.3。
cryptography 原生模块动态链接审计仅发现系统库。
本实验未证明构建结果可逐字节复现。

项目内产物目录：
artifacts/intel-crypto-37679350161/

Release 草稿标签：
deps-cryptography-50.0.0-macos15-intel-r1

## 验证边界与待办

- 未验证国内网络完整安装链、模型对话、浏览器组件及其他可选功能。
- 未验证其他 macOS、Linux 发行版或 Python 版本。
- 构建依赖有版本约束，尚无完整哈希锁定。
- CLI 显示更新提示，不能宣称启动完全不联网。
- 保持固定上游版本，不以 hermes update 替代适配发布流程。
- wheel 自带 cryptography 许可证，但未检出 OpenSSL 独立声明。
- OpenSSL 及其他静态链接组件的许可证资料仍待核实补齐。
- Release 仍为草稿，未公开发布。
- CI 仍引用 Actions 产物 11507708102，预计于
  2026-10-14 20:08:14 UTC 到期；尚未切换持久下载地址。

## 归档规则

需要长期保留的文档存放在项目 docs/ 下，并纳入 Git。
二进制文件存放在项目 artifacts/ 下，不纳入 Git。
原项目外归档保留，待用户自行决定是否清理。
