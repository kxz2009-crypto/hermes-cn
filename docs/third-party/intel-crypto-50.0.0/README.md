# Intel cryptography 50.0.0 许可证资料

状态：资料收集阶段，尚未完成再分发声明审查。

## 来源

- cryptography 三份许可证直接来自已验证的自建 wheel。
- OpenSSL 文件来自官方仓库 openssl-3.6.3 标签解析后的 commit。
- cryptography 源码包根据固定 Hermes commit 的 uv.lock 定位并校验。
- Cargo.lock 从校验通过的源码包读取，未执行或展开源码到工作目录。
- 二进制和源码归档存放于项目 artifacts/，不纳入 Git。

## 证据边界

- 官方 OpenSSL 标签的许可证资料不等同于完整的 Homebrew 构建来源记录。
- Cargo.lock 包含候选依赖，可能涉及构建、测试或其他平台；
  不能据此认定所有条目均进入已构建 wheel。
- 仍需核查实际进入二进制的 Rust 等组件，以及其许可证与 NOTICE。
- 本次不修改 wheel、不改变哈希、不公开 Release。
- 在完成核查前，保留 Release 草稿及原有待办状态。
