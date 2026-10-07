# Intel wheel 草稿附件访问验证

## 本地验证

用户提供的执行结果确认：
- Release asset ID：619728415。
- 文件：cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl。
- 大小：3838299 字节。
- SHA256：bb6320d4dc523339041c40e58176beb3235d59c133968490694fd1924c68c49c。
- 已登录账号认证下载并校验通过。
- 原始资料：artifacts/intel-draft-download-check/。

## Actions 验证

新增手动工作流 draft-asset-access.yml。
仅授予 contents: read，不使用个人访问令牌。
验证固定附件元数据、实际下载及 SHA256。

结果待运行确认。
本工作流不修改现有 core-deps-probe.yml，
不发布 Release，不代表第三方声明审查完成。
