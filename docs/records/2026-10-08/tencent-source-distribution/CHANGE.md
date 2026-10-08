# 腾讯云固定源码分发

安装器改为从 LocalVRAM 腾讯云下载源码包。
校验内置 SHA256、归档路径和文件类型后，
从本地浅 Git 仓库恢复原始固定提交。

- 上游提交：f97608f178d1ffeca59860195ab7da295f7c8e5f
- 源码包 SHA256：c6a92c0e9d06f69714e4b194584891a6c27e45870ad40f4a3db1293db6cd9b58
- 下载地址：https://hermes.localvram.cn/downloads/hermes-source/f97608f178d1ffeca59860195ab7da295f7c8e5f/hermes-source-f97608f178d1ffeca59860195ab7da295f7c8e5f.tar.gz
- 同目录提供上游许可证、来源说明和校验清单。
- Git origin 保留原始上游地址。

用户提供的执行结果：
服务器本机 HTTPS、WSL 公网下载及包哈希校验通过；
本次公网下载耗时 227 秒，平均约 338 KB/s；
候选源码获取步骤使用缓存包恢复固定提交通过；
损坏包在解包前被拒绝，未创建源码仓库。

上述速度仅代表本次网络条件。
Python、依赖和 Intel wheel 下载逻辑未改变。
完整安装回归由本提交触发的六组 CI 验证。
网站固定版本尚未切换。
