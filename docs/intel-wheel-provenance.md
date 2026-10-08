# Intel wheel 构建来源补充

原构建 37679350161 的日志记录 OpenSSL 3.6.3，
但没有保存 Homebrew 安装收据或静态库哈希。

本次修改在新构建中采集：
- 当前运行、提交、runner 镜像、系统与 Python 版本。
- Homebrew OpenSSL 安装收据及其哈希。
- libcrypto.a、libssl.a 的路径、大小与 SHA256。
- 安装目录中的许可证与 NOTICE 原文。
- Rust、Cargo、Clang、SDK、OpenSSL 和 Python 构建包版本。
- 已通过上游锁文件校验的 cryptography 源码包哈希。
- 构建后的静态库哈希复核及产物文件哈希清单。

保留原有原生库链接审计、独立环境安装和加密签名测试。
附件名称增加 provenance，保留期调整为 30 天。

这些记录只适用于新构建，不能追认旧 wheel 的来源。
安装收据不等于完整可复现构建证明。
实际链接的 Rust 组件清单仍未由本步骤确定。
新 wheel 尚未接入安装器；原 wheel、Release 草稿及核心 CI 不变。
