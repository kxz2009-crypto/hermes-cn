# 国内 GLM Coding Plan API 测试

模型：glm-5.3-flash。
接口：https://open.bigmodel.cn/api/coding/paas/v4。
结果：PASS；返回 GLM_CONNECTION_OK，finish_reason 为 stop。
耗时：4.08 秒；总 token：74。

测试使用独立安装环境中的 OpenAI SDK，自动重试关闭。
密钥在本地从既有 .env 读取，没有归档密钥。
本次没有启动 Hermes agent，没有发送工具定义。

本记录仅证明该 WSL 环境下的一次 SDK 调用成功，
不代表 Hermes 对话、工具调用或腾讯北京网络测试通过。
