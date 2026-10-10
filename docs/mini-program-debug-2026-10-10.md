# 微信小程序代码调试记录 · 2026-10-10

AppID：wx9e5937d752f2125f。当前为本地演练，真实付款未启用。

## 修复
- 错误关联码进入页面时，onShow 不再将此前检查通过的缓存覆盖到新关联结果；错误期间隐藏继续下单入口。
- 订单刷新成功清除旧错误提示，覆盖确认订单页和结果页。

## 已验证
- 12 项 Node 业务、服务及页面操作回归测试通过。
- 微信开发者工具安装包自带 wcc.exe：七个 WXML 页面编译退出码 0，无 stderr。
- 自带 wcsc.exe：app.wxss 与七页样式编译退出码 0，无 stderr。
- 原源码、用户已导入的 outputs/hermes-cn-mini-program 和交付 ZIP 已同步；保留开发者工具本机 private 配置。

## 尚未验证
完整 IDE 构建、模拟器点击与布局、视频播放、Android/iOS 真机：未执行。
官方 CLI auto 因 IDE service port disabled 无法连接；桌面控制工具仍报告 sandboxCwd 兼容错误。
编译器级通过不能替代完整 IDE 与设备验收。等待用户开启服务端口后继续模拟器调试。
