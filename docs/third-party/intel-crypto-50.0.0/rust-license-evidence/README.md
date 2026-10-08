# Rust 候选依赖许可证证据

来源：固定 cryptography 源码 Cargo.lock 对应的候选依赖清单。

- registry 包从 static.crates.io 下载。
- 每个源码包按候选清单中的锁文件 SHA256 校验。
- JSON 保存 Cargo.toml 声明及包内许可证、NOTICE 等原文与哈希。
- 源码包保存在项目 artifacts/rust-license-sources。
- 未执行源码，未解包到文件系统，未编译。
- 无 registry 来源的 cryptography 内部组件未单独下载。
- 未将候选依赖自动判定为实际链接组件。
- 资料收集不等于再分发审查完成。
- 尚需核查遗漏声明、内部组件与 OpenSSL 构建来源。
