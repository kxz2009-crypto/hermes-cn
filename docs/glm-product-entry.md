# 国内 GLM Coding Plan 入口

新安装生成 bin/hermes-glm：
- setup：隐藏输入密钥，保存至独立 state/glm-coding.env，已有文件不覆盖。
- status：检查凭据文件权限、所有者与字段，不联网。
- check：调用实际 Hermes CLI，输出 JSON 检查结果，可能消耗套餐额度。
- chat：交互对话，可追加 Hermes chat 参数。

默认 provider=zai，模型 glm-5.3-flash，
接口 https://open.bigmodel.cn/api/coding/paas/v4。
status 成功不证明密钥有效或服务可用。

错误分类采用 CLI 文本模式，不能区分所有业务原因。
check 不回显原始响应；日常 chat 使用上游交互输出。
safe-mode 不等同于禁用所有工具。
独立启动器关闭隐式依赖安装，可选功能须另行安装和验收。

离线检查覆盖帮助、未配置、拒绝覆盖、错误分类、语法及嵌入一致性。
隐藏输入和成功保存凭据的完整交互流程仍待验证。
真实服务器 GLM 对话仍记录为 HTTP 429 未通过。
已有安装不会自动升级；网站仍固定先前验收版本。
