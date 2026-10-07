# uv 自举与 Python 命令链接隔离修正

依据：用户提供的 WSL 终端执行结果。

- 项目独立 uv：0.12.23。
- 工具路径：artifacts/bootstrap-uv-0.12.23/venv/bin/uv。
- 下载来源：TUNA；终端显示 wheel 大小 20.6 MB。
- 现用 /home/gao20/.local/bin/uv：仍为 0.10.9。
- 本步骤未执行 Hermes 安装。
- uv 自举使用版本固定与 HTTPS，未提供预先固定的 wheel 哈希。

## 修正

此前安装器设置 UV_PYTHON_INSTALL_DIR，但未禁止默认 bin 链接写入。
根据该版本帮助，将命令改为：

uv python install --no-bin 3.11.17

此选项限制该 Python 安装步骤的命令链接行为，
不构成对整个安装器或运行时所有文件访问的沙箱保证。

修改后的 CI 结果待核实。
