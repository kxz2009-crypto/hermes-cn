# Intel 自动下载路径验收

主 CI 在 macOS 15 Intel × PyPI/TUNA 两组增加独立安装测试。
新目录 lite-auto-download 不传 --intel-wheel，
调用当前提交的安装器，实际执行公开 Release 自动下载。

验收项目：
- 安装完成标记和固定上游提交；
- 安装器内部 CLI 帮助及版本检查；
- 分发包、声明和来源文件留存；
- 随包 SHA256SUMS 校验；
- 下载 wheel 与安装用 wheel 均匹配固定 r2 SHA256；
- cryptography 版本及构建来源身份。

既有显式本地 wheel 安装和错误哈希阻断测试保留。
本测试不执行模型请求，不需要 API 密钥。
测试结果以对应 GitHub Actions 运行记录为准。
