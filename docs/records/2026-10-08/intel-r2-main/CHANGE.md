# r2 接入主安装器与主 CI

## 变更

主安装器 Intel wheel 校验值切换至已通过候选集成测试的 r2。
主 core-deps-probe 工作流同时切换 artifact、构建运行、
构建提交、ZIP 哈希和 wheel 哈希。

wheel SHA256：
11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f

构建运行：37719594029。
候选集成运行：37720428375。
候选测试覆盖 Intel macOS 15 × PyPI/TUNA。

此次回归验证仓库主安装器和主工作流的实际组合，
不重新构建 wheel。

## 声明材料处理结论

- wheel 原有三份 cryptography 许可证与归档逐字节一致。
- 构建环境 OpenSSL 许可证与归档官方版本逐字节一致。
- self_cell 的 Apache-2.0 OR GPL-2.0-only 声明允许选择
  Apache-2.0；不得仅因归档含 GPL 文本而认定整个 wheel 为 GPL。
- target-lexicon 保留 Apache-2.0 WITH LLVM-exception 全文。
- unicode-ident 保留 Unicode-3.0 及其 MIT/Apache 选择项。
- 历史 MIT/Apache-2.0 写法保持原文，不自动改写声明。
- 保留各组件版权声明及原始许可证文本。

以上是现有声明材料的处理结论，
不是完整链接组件清单或无遗漏的法律合规保证。

参考：
https://spdx.github.io/spdx-spec/v3.0.1/annexes/spdx-license-expressions/
https://www.apache.org/licenses/LICENSE-2.0

## 接入边界

Intel 安装仍需要显式提供本地 r2 wheel。
CI 当前仍通过 Actions artifact 下载，尚未完成持久下载接入。
原候选工作流保留用于追溯；其临时旧哈希替换逻辑需在
后续清理时停用，不应再对当前 main 重复触发。
本次不公开 Release。
