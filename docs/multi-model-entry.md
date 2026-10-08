# 多模型入口（候选）

新增：
- hermes-cn model list
- hermes-cn model setup [预设名称] [新配置名称]
- hermes-cn model use 配置名称
- hermes-cn model status [配置名称]
- hermes-cn model check [配置名称]
- hermes-cn chat

预设：GLM Coding Plan、DeepSeek Flash/Pro、Kimi Coding Plan、
豆包、Qwen、MiniMax、MiMo、腾讯 HY3、Custom。

协议范围：OpenAI Chat Completions 兼容接口。
豆包模型 ID、MiniMax 接口和模型由用户按控制台填写。
其他预设允许在配置时调整地址和模型，须匹配地区、套餐及密钥。
Kimi 使用 Coding Plan，保持真实客户端身份，不伪装其他客户端。

每个配置保存在安装目录 state/models/<名称>/config.yaml。
文件包含密钥，权限 600；不要上传、提交或分享该文件。
每个配置使用独立 HERMES_HOME，因此会话、记忆及其他状态相互独立。
setup 拒绝覆盖；更换密钥可创建另一个配置名称。
use 只影响以后通过此入口启动的会话。
list/status/setup/use 不请求模型；check/chat 会消耗服务商额度。
已有 hermes-glm 入口保留；未选择新配置时原有 chat 路径保留。
本版多模型 chat 不接受附加参数，避免覆盖所选模型或接口。

本地离线检查通过不代表 Hermes 路由、真实认证、工具调用或对话验收通过。
安装器仍限制为 Linux x86_64 和 macOS 15 arm64/x86_64。
现有安装不会因修改仓库安装器自动升级。
