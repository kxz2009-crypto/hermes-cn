# 北京服务器安装恢复与本地版本检查

依据：用户提供的服务器执行结果；非远程代执行。

## 环境与结果

- OpenCloudOS 9.4，Linux x86_64。
- 独立账号：hermes-cn-test。
- 安装目录：/srv/localvram/hermes/product-test/install。
- Hermes 上游：f97608f178d1ffeca59860195ab7da295f7c8e5f。
- Hermes 0.21.5；Python 3.11.17；OpenAI SDK 2.24.0。
- Python 下载及安装耗时：27.03 秒。
- uv pip check：63 个包检查通过。
- 修改启动器后 --version：通过，0.19 秒。
- --help：通过，0.71 秒。
- 上游已跟踪源码未修改。
- 恢复验收通过后生成安装成功标记。

## 故障与修复

服务器首次安装及有限重试均未能完成上游 Git 源码下载。
恢复使用 WSL 的固定提交源码，经 SSH 传输并校验。
Python 和依赖随后由服务器下载。

原 --version 验收超过 60 秒。
上游 print_fast_version_info 默认同步检查更新。
独立启动器对单独的 --version 参数调用同一函数，
显式设置 check_updates=False；其他参数继续传给原 CLI。
此调整在服务器复测通过，本提交将其纳入安装器模板。

## 证据位置

服务器：
- records/offline-source-20261008T045959Z/install.log
- records/local-version-20261008T050845Z/verification.log
- records/local-version-20261008T050845Z/ACCEPTANCE.txt

上述路径相对于 /srv/localvram/hermes/product-test。

## 边界与待办

本次是恢复安装通过，不是公开安装器首次自动安装通过。
尚需提供固定源码的备用下载方式，并验证干净目录安装。
本服务器的模型对话尚未验收。
此次只调整版本查询，不保证其他 CLI 命令不进行更新检查。
