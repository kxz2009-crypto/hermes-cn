# Intel 候选 wheel 集成验收

- 测试提交：3ad27c546ad2abf903b8e4ba9f8043749394a2d8
- 运行：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37720428375
- 构建运行：37719594029。
- 候选 artifact：11524969260。
- wheel SHA256：11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f。

| 测试组合 | 结果 |
| --- | --- |
| macos-15-intel / pypi | PASS |
| macos-15-intel / tuna | PASS |
## 验收范围

两组均通过核心依赖校验、加密测试、Hermes editable 安装、
CLI 启动、轻量安装器及保护测试。
上游 pyproject.toml 和 uv.lock 未修改。

安装器测试使用 runner 临时副本，将两个旧 wheel 哈希替换为
候选哈希；仓库中的正式安装器仍引用旧 wheel。

## 后续接入边界

本次支持将新 wheel 作为下一版集成候选。
未验证 Intel 实机模型对话或中国大陆完整下载链。
当前下载仍依赖 Actions artifact，不是持久分发渠道。
第三方声明草稿与来源记录继续保留，不将其描述为完整 SBOM。
本次未发布 Release。
