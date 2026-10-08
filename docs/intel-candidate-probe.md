# Intel 新 wheel 集成测试

手动工作流：intel-candidate-probe.yml。
矩阵：macos-15-intel × PyPI/TUNA。

从现有核心依赖工作流派生，沿用：
- 固定上游锁文件导出与依赖哈希校验。
- Hermes editable 安装及 CLI 启动。
- 轻量安装器与保护边界测试。

候选 artifact：11524969260。
构建运行：37719594029。
wheel SHA256：
11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f

安装器测试仅在 runner 临时副本中替换两个固定哈希。
保护测试使用同一临时副本。
项目 scripts/install-lite.sh 和原核心工作流不变。

本工作流测试候选集成，不代表公开发布或持久分发完成。
