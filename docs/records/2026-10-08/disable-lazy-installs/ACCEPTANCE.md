# 轻量安装的运行时自动安装策略

## 问题与修复

北京测试环境中，GLM CLI 初始化路径导入 Bedrock 适配器，
触发 boto3 的 lazy dependency 安装，导致启动等待超时。

安装器生成的启动器设置 HERMES_DISABLE_LAZY_INSTALLS=1，
并清除 HERMES_LAZY_INSTALL_TARGET，关闭此自动安装机制。
保留本地 --version 检查，不修改上游源码。

## 服务器实测

依据：用户提供的服务器终端输出。

- 记录：/srv/localvram/hermes/product-test/records/disable-lazy-installs-20261008T053658Z
- 上游 _allow_lazy_installs() 返回 False。
- Hermes 0.21.5、Python 3.11.17、OpenAI SDK 2.24.0。
- 修改后的启动器版本与帮助命令通过。
- 此次验证未发送模型请求。

此前禁用自动安装后的 GLM CLI 诊断输出 HTTP 429，
进程退出码为 1，对话验收未通过。
尚不能区分额度、并发或请求频率限制。

## 产品边界

可选功能所需额外依赖须显式安装并单独验收。
此设置不阻止工具执行安装命令，不等同于操作系统沙箱。
网络测试涉及代理条件，下载失败原因尚未确定。
本修复不构成中国大陆无代理完整安装验收。

本记录的服务器结果不代替本提交的 CI 结果。
