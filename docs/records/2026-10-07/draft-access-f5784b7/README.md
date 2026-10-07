# Release 草稿附件：Actions 只读访问测试

## 证据

依据：用户提供的 GitHub Actions 运行结果及日志。

- 工作流提交：f5784b75b1ebc1e358e36bf4ee38f347e26fe892。
- 运行：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37690328471。
- 仓库：kxz2009-crypto/hermes-cn。
- Release asset ID：619728415。
- GITHUB_TOKEN 权限：contents: read、metadata: read。
- 失败位置：获取附件元数据的首个 API 请求。
- 返回：Resource not accessible by integration (HTTP 403)。
- 尚未执行附件下载与 SHA256 校验。

此前使用本地登录账号下载同一附件并校验 SHA256 成功。
两次测试使用不同凭据，不能混同其访问能力。

## 决定

本次结果不支持以只读 GITHUB_TOKEN 接入该草稿附件。
停止此路线的重复测试，不增加写权限，不引入个人令牌。

核心依赖工作流暂保留原 Actions artifact：
- ID：11507708102。
- 到期时间：2026-10-14T20:08:14Z。
- 本地项目归档和 Release 草稿继续保留。
- 本地备份不等于 CI 已具备持久下载能力。

下一步完成第三方声明资料核查，准备实验依赖发布资料，
再接入持久下载来源。当前未发布 Release，未修改核心 CI。

本结论仅适用于本次仓库、草稿附件及令牌权限组合。
