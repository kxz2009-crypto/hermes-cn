# Intel r2 持久下载接入

macOS 15 Intel 安装时未提供 --intel-wheel，
安装器自动下载固定 GitHub Release 的 r2 分发包。

ZIP SHA256 固定在安装器中，来自此前提交并验证的校验清单。
ZIP 校验通过后按明确文件名读取附件，再次校验 wheel。
声明及构建来源保留在安装目录/work/intel-bundle/。

--intel-wheel 仍支持固定 r2 本地文件，
并在创建安装目录前校验文件名和 SHA256。
使用本地文件方式时，应同时保留随分发包提供的声明与来源。

主 CI 改用公开 Release，不再依赖临时 Actions wheel artifact。
此前摘要中的 artifact ID 和过期日期同步替换。

现有安装器集成测试仍传入本地 wheel，
自动下载分支尚需独立覆盖。
下载失败保留现场；当前不支持复用失败安装目录。

本版本为实验预发布，不保证所有国内网络可达。
第三方声明保留原有审查范围说明。
