# Intel 新构建证据核对

- 构建运行：37719594029。
- 构建提交：1b3d7ea78cdc8f86150028c7a31959fee6e56005。
- 新 wheel SHA256：11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f。
- ZIP 与内部文件清单校验通过，见下载执行记录。
- 构建、链接审计、加密签名测试通过，见 run.json。
- OpenSSL 安装目录许可证与已归档官方许可证逐字节比较：一致。

## 采集范围说明

installed_notices 中的 NOTICEREF_free.3ssl 和 NOTICEREF_new.3ssl
属于手册页误匹配，不作为许可证或 NOTICE 使用。
原始 build-inputs.json 保留不改。

## 验证边界

安装收据和静态库哈希用于追溯本次构建输入，
不等于完整可复现构建证明或实际 Rust 链接组件清单。
新 wheel 尚未通过 Hermes 集成测试，未替换安装器固定资产。
本记录不表示 Release 发布批准。
