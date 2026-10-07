# 实验轻量安装器 CI 验收

- Commit：`02a0e9370de62881e0ae9c9796216f1fe1dbad47`
- 运行记录：https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37683668649
- 结果：六组安装器步骤全部通过。

| 平台 / 来源 | 安装器测试 |
| --- | --- |
| macos-15 / pypi | PASS |
| macos-15 / tuna | PASS |
| macos-15-intel / pypi | PASS |
| macos-15-intel / tuna | PASS |
| ubuntu-24.04 / pypi | PASS |
| ubuntu-24.04 / tuna | PASS |

## 验证范围

独立目录安装、核心依赖校验、Hermes editable 安装、
hermes-cn 帮助与版本命令启动、成功标记检查。

## 限制

- 使用 GitHub runner，尚未验证国内网络完整下载链。
- 需要预先提供 uv 0.12.23；Intel 需要已验证的 wheel。
- 未验证模型对话、浏览器组件及其他可选功能。
- 未完成重复安装拒绝、失败场景及现有环境不受影响的专项测试。
- CI 仍依赖临时 Actions wheel 产物，持久下载接入尚未完成。
- 当前为实验版，不是正式发布验收。

