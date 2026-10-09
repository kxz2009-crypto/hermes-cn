# 问答限额候选（Phase 2 · 未部署）

生成日期：2026-10-09。本目录是**候选与离线测试**，线上服务
（hermes-install-assistant.service，127.0.0.1:3016）已在运行同方案代码。

## 内容

| 文件 | 说明 | 与线上对照 |
| --- | --- | --- |
| assistant_app.py | 助手核心（校验/脱敏/模型调用） | 逐字节一致 |
| quota.py | SQLite 限额（分钟/日/全站/并发） | 逐字节一致 |
| guarded_app.py | X-Real-IP 门控 + 限额接入 | 逐字节一致 |
| test_quota.py | 14 项离线单元测试（本轮新写） | 线上无，仓库新增 |

线上哈希对照（2026-10-09 实测一致）：

```
ed42e7c6da3ca79bc8d2218809125fad1a34452986f7df52588d1322b073fcb0  assistant_app.py
3c3d1cde8a62cf822b80f7b640fc5328e4c2787ce9017f7087944c2b163e7237  quota.py
29377f08b9470c4d8944390fabd15646dc9b7dd45c3952a3a7b8fb369850e777  guarded_app.py
```

## 限额设计（与需求逐条对应）

- 同一网络地址每分钟 3 次 / 每天 20 次：`ip-minute` / `ip-day` 桶。
- 全站每天 100 次模型请求尝试、同时最多 2 个：`global:{day}` 桶 + `leases` 表。
- 计数写 SQLite，重启不清零（test_persistence_across_restart 验证）。
- 按北京时间每日切换：day = (epoch + 28800) // 86400（test_beijing_day_rollover 验证）。
- 只存计数与 HMAC-SHA256(日密钥, 地址) 标识；不存明文地址
  （test_identity_not_reversible 验证）；不存问题/回答/密钥。

## 离线测试结果

```
python3 -m unittest test_quota.py -v
Ran 14 tests in 0.431s — OK
```

## 服务器实测（2026-10-09，本机模拟公网来源）

- 每分钟第 4 次请求 → 429（生产库测试后已清理计数）。
- 并发第 3 个 lease 被拒，释放后可进入。
- 全站 global_day 缩小为 3 模拟：第 4 次被拒。

## 部署状态

线上已在运行同方案（systemd: hermes-install-assistant.service，当前
is-enabled=disabled，即未开机自启）。本目录作为代码入库基线；
后续部署动作须单独走审批流程，本候选不触发任何部署。
