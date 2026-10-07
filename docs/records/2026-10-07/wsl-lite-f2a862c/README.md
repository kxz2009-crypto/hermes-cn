# WSL 独立目录安装实测

## CI 前置依据

- 提交：f2a862ca4114bad309481a216871c3435d135738
- 运行：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37686781981
- 依据：用户提供的 GitHub CLI 查询结果。
- Ubuntu 24.04、macOS 15 ARM、macOS 15 Intel × PyPI/TUNA：
  六组安装器与保护测试均成功。
- 本轮包含 Python 安装 --no-bin 修正。

## 本地测试安排

安装目标：项目 artifacts/wsl-lite-f2a862c。
工具：项目独立 uv 0.12.23。
依赖源：TUNA；源码及解释器仍使用上游下载。
以清理后的子进程环境运行，不继承 API 密钥或显式代理变量。
保留真实 HOME；目录隔离不等同于操作系统沙箱。
不运行 setup、模型对话、浏览器或服务安装。

安装结果以本目录 result.txt 和终端输出为准。
完整日志保存在项目 artifacts 下，不自动提交到公开仓库。
本测试不能代表腾讯北京节点或国内其他网络。
