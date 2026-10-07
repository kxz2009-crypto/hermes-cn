# Hermes Agent 核心 GLM 调用记录

## 实测结果

- Hermes 上游：f97608f178d1ffeca59860195ab7da295f7c8e5f。
- 安装器版本：f2a862ca4114bad309481a216871c3435d135738。
- 模型：glm-5.3-flash。
- 接口：https://open.bigmodel.cn/api/coding/paas/v4。
- 入口：AIAgent Python API。
- 回复：HERMES_GLM_OK。
- 耗时：20.51 秒。
- 请求前后工具数：均为 0。
- 返回消息中工具调用：无。

## 测试范围

独立安装环境、独立 HERMES_HOME、显式空工具列表。
关闭上下文文件读取、记忆和后台复盘。
密钥从本地既有 .env 提取，没有归档密钥。
probe.py 为本次实际测试脚本，保留原样用于追溯。

## 验收脚本局限

原脚本检查 answer.get("error")，而返回结构使用
failed、completed、interrupted、partial 等状态字段。
这些状态值没有保存，agent_error_present=false 不足以证明全部正常。
本次确认核心调用取得预期回复，不作为完整 CLI 验收。

尚未验证 CLI 模型路由、工具调用、腾讯北京完整安装，
也未完成 Intel 持久资产分发与再分发声明核查。
