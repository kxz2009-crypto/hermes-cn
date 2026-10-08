# LocalVRAM · Hermes 多模型安装指南

下载说明：支持国内网络下载安装，已完成 Windows／WSL 实机安装及 DeepSeek 对话验证。

本项目是独立社区适配项目，与 Nous Research 无隶属关系，亦未获得其背书。

## 1. 建议安装门槛

以下为本项目主动提高的配置门槛，不是 Hermes 官方最低配置，也不是性能测试结论。

- Windows：Windows 11 x64、4 核 CPU、16 GB 内存、WSL2 + Ubuntu 24.04、至少 20 GB 可用 SSD 空间。
- Apple Silicon Mac：macOS 15、M1 或更新芯片、16 GB 内存、至少 20 GB 可用 SSD 空间。
- Intel Mac：macOS 15、4 核 Intel CPU、16 GB 内存、至少 20 GB 可用 SSD 空间。
- Linux：Ubuntu 24.04 x86_64、4 核 CPU、16 GB 内存、至少 20 GB 可用 SSD 空间。
- 更推荐：Windows、Intel Mac、Linux 使用 32 GB 内存；Apple Silicon 使用 24 GB 或以上内存；预留 40 GB 磁盘空间。
- Windows 需启用 CPU 虚拟化，建议 WSL 可用内存至少 8 GB。
- 安装前关闭不必要的大型程序，建议保留至少 4 GB 可用内存。
- 使用本机 SSD 用户目录，避免网络盘、移动硬盘和云盘同步目录；安装路径不能包含空白字符。
- 本版调用云端模型，不要求独立显卡或 CUDA。本地模型需要另行评估硬件。
- 当前不支持 Windows 原生安装、Windows ARM、Linux ARM；Mac 当前仅允许 macOS 15。

安装器尚未强制检查全部硬件门槛。配置达标不等于网络和所有可选功能均可用。

## 2. Windows：准备 Ubuntu

已安装 WSL 的用户在 PowerShell 检查，不必重复安装：

```powershell
wsl -l -v
```

确认 Ubuntu 24.04 的 VERSION 为 2。
尚未安装的用户，在管理员 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

按提示重启并完成 Ubuntu 用户名、密码设置。
输入 Linux 密码时不显示字符，这是正常现象。

从开始菜单打开 Ubuntu，准备工具：

```bash
cd ~
sudo apt-get update
sudo apt-get install -y git curl python3 python3-venv ca-certificates
```

后续 Bash 命令均在 Ubuntu 中运行，不在 PowerShell 或 CMD 中运行。
Hermes 安装使用普通用户，不使用 sudo，也不要从 Windows/System32 目录开始。

## 3. Mac：准备终端

通过苹果菜单“关于本机”确认系统版本、芯片和内存。
当前仅允许 macOS 15，不是“15 及以上”。

按 Command + 空格搜索“终端”。Apple Silicon 使用原生终端，不启用“使用 Rosetta 打开”。

```bash
sw_vers -productVersion
uname -m
git --version
python3 --version
curl --version
command -v unzip
command -v shasum
python3 -c 'import venv, ensurepip, ssl; print("Python 准备条件通过")'
```

Apple Silicon 原生架构显示 arm64；Intel Mac 显示 x86_64。
若 Apple Silicon 显示 x86_64，先检查 Rosetta 设置。

Git 如提示安装 Apple 命令行工具，先完成安装。
缺少 Python 或模块检查失败时，先从 Python 官网安装适合本机架构的 Python 3.11 或更新版本：
https://www.python.org/downloads/macos/

Hermes 自身运行时由安装器另行固定为 Python 3.11.17。
Mac 不运行 wsl，不使用 sudo 执行 Hermes 安装。

## 4. 网络与账号

安装需要保持网络连接。下载失败时，请保留错误输出和安装目录。
Intel Mac 所需专用依赖包由安装器自动下载并校验。
模型需要对应 API Key 和可用额度；网页会员不一定包含 API 权限。
普通 API、Coding Plan 和不同地区接口的密钥不能随意混用。
遇到 EOF 或超时，保留错误输出，不关闭证书验证，不反复删除安装目录。
当前尚未完成全部中国大陆网络的安装验证。

## 5. 安装多模型版

Windows 用户在 Ubuntu 内运行；Mac 用户在终端运行；Linux 用户在普通用户终端运行。

一次复制完整代码框，不复制用户名、命令提示符或运行结果。
本指南使用新的 r3 目录，保留旧 r2 安装，不自动迁移旧密钥、记忆或会话。
第一次安装失败后，目录存在会阻止重复安装；保留错误输出，不要直接删除目录。

下面的命令会安装独立工具、固定版本 Hermes 及依赖，但不会申请 API Key 或请求模型。

```bash
bash << 'INSTALL'
set -euo pipefail
umask 077

tools="$HOME/.local/share/hermes-cn-tools-r3"
adapter="$HOME/.local/share/hermes-cn-adapter-r3"
prefix="$HOME/.local/share/hermes-cn-lite-r3"
commit=386147344dee20b2921da4afb40c188d6beda499

[ "$(id -u)" -ne 0 ] || {
  echo '请使用普通用户安装，不要使用 root 或 sudo。'
  exit 1
}

case "$HOME" in
  *[[:space:]]*)
    echo '主目录包含空白字符，请停止并寻求帮助。'
    exit 1
    ;;
esac

case "$(uname -s)/$(uname -m)" in
  Linux/x86_64) ;;
  Darwin/arm64|Darwin/x86_64)
    [ "$(sw_vers -productVersion | cut -d . -f 1)" = 15 ] || {
      echo '本版仅允许 macOS 15。'
      exit 1
    }
    [ "$(sysctl -in sysctl.proc_translated 2>/dev/null || true)" != 1 ] || {
      echo '请使用非 Rosetta 的原生终端。'
      exit 1
    }
    ;;
  *)
    echo '当前平台不在本版支持范围。'
    exit 1
    ;;
esac

for tool in git curl python3; do
  command -v "$tool" >/dev/null || {
    echo "缺少工具：$tool，请先完成准备步骤。"
    exit 1
  }
done
git --version
python3 -c 'import venv, ensurepip, ssl'

if [ "$(uname -s)/$(uname -m)" = Darwin/x86_64 ]; then
  command -v unzip >/dev/null
  command -v shasum >/dev/null
fi

for path in "$tools" "$adapter" "$prefix"; do
  if [ -e "$path" ] || [ -L "$path" ]; then
    printf '目录已存在，请保留现场，不要重复安装：%s\n' "$path"
    exit 1
  fi
done

mkdir -p "$HOME/.local/share"

printf '\n===== 1. 准备独立安装工具 =====\n'
python3 -m venv "$tools"
"$tools/bin/python" -m pip --isolated install \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple \
  'uv==0.12.23'

printf '\n===== 2. 获取固定安装器 =====\n'
mkdir -p "$adapter"
installer_url="https://hermes.localvram.cn/downloads/installers/$commit/install-lite.sh"
installer_hash=8315f40752f0149e5e1d8b97f3926153d49a16189f3f362c047b559ca35152d7

downloaded=0
for attempt in 1 2 3; do
  printf '安装器下载尝试：%s/3\n' "$attempt"
  if curl -q --fail --silent --show-error --location \
    --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 90 --retry 0 \
    "$installer_url" |
    cat > "$adapter/install-lite.sh"; then
    downloaded=1
    break
  fi
  if [ "$attempt" -lt 3 ]; then sleep 3; fi
done

[ "$downloaded" -eq 1 ] || {
  echo '安装器下载失败，请保留错误输出和安装目录。'
  exit 1
}

python3 - "$adapter/install-lite.sh" "$installer_hash" << 'VERIFY_INSTALLER'
import hashlib
from pathlib import Path
import sys
actual = hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest()
if actual != sys.argv[2]:
    sys.exit("停止：安装器校验不通过，未执行。")
print("PASS：固定安装器 SHA256 校验")
VERIFY_INSTALLER

bash -n "$adapter/install-lite.sh"

printf '\n===== 3. 安装 Hermes =====\n'
bash "$adapter/install-lite.sh" \
  --prefix "$prefix" \
  --uv "$tools/bin/uv" \
  --source tuna

[ "$(cat "$prefix/INSTALL_COMPLETE")" = experimental-lite-0.1 ]
"$prefix/bin/hermes-cn" --version
"$prefix/bin/hermes-cn" model list
printf '\n安装完成。下一步配置模型 API Key。\n'
INSTALL
```

安装成功时，可以看到版本信息、模型列表和“安装完成”。
如果出现 fatal、Traceback 或下载失败，请保留最后的错误信息，不要继续执行模型配置。


## 6. 第一次配置模型：以 DeepSeek 为例

安装完成后运行：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model setup deepseek
```

- Base URL：直接回车，保留预设地址。
- 模型 ID：直接回车，保留 deepseek-flash。
- API Key：粘贴自己申请的 DeepSeek API Key，再回车。
- 密钥输入时不显示字符或星号，这是正常现象。不要把密钥贴到聊天、截图或问题反馈中。

选择配置，再检查本地状态：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model use deepseek
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model status
```

status 不发送请求，不代表密钥有效或账户有额度。
真实对话检查使用下面的命令，可能消耗额度，最长等待约 120 秒：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model check
```

结果出现 "status": "PASS"，表示本次对话检查通过。
如果失败，先处理错误提示，不要反复执行安装。

## 7. 配置其他模型

查看预设：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model list
```

- glm：GLM Coding Plan，默认 glm-5.3-flash。
- deepseek：DeepSeek 普通 API，默认 deepseek-flash。
- deepseek-pro：DeepSeek 普通 API，默认 deepseek-v4-pro。
- kimi：Kimi Coding Plan，默认 k3；需有对应模型权限，不是普通 Moonshot API。
- doubao：火山方舟普通 API；模型 ID 按自己的控制台填写。
- qwen：百炼北京区普通 API，默认 qwen-plus；不是百炼 Coding Plan。
- minimax：按自己的控制台填写 OpenAI 兼容 Base URL、模型 ID 和密钥。
- mimo：小米 MiMo，默认 mimo-v2.5-pro。
- hy3：腾讯 TokenHub，默认 hy3，使用 TokenHub 对应密钥。
- custom：自己填写 HTTPS Base URL、模型 ID、API Key。

预设与配置入口不等于各家真实模型均通过验收。
填写时确认接口、地区、套餐及密钥相匹配。服务商模型和套餐可能变化，以本人控制台为准。

例如配置 Kimi Coding Plan：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model setup kimi
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model use kimi
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model status
```

Kimi 需填写 Kimi Coding Plan 的密钥；模型提示可按套餐权限修改。
其他模型同理，将 setup 和 use 后面的名称替换为相应预设名称。

例如配置自定义服务：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model setup custom
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model use custom
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model status
```

Custom 本版只支持 OpenAI Chat Completions 兼容协议。
填写服务商提供的 Base URL，例如 https://example.com/v1；不要额外加 /chat/completions。
不要使用仅支持 Anthropic Messages 或 Responses 的地址，也不要将密钥放入 URL。
上面的 example.com 只是格式示例，不是可用模型服务。

已有配置拒绝覆盖。更换密钥时可以创建新名称：

```bash
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model setup deepseek deepseek-new
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" model use deepseek-new
```

每个配置的密钥、会话、记忆和状态独立，切换后不会自动继承另一配置的历史。
use 影响随后新启动的聊天，不改变正在运行的会话。
配置文件保存在安装目录的 state/models 下，包含密钥；不要上传或分享这些文件。

## 8. 每天如何开始聊天

Windows 打开 Ubuntu；Mac 打开终端。运行：

```bash
mkdir -p "$HOME/hermes-work"
cd "$HOME/hermes-work"
"$HOME/.local/share/hermes-cn-lite-r3/bin/hermes-cn" chat
```

可先输入：你好，请用中文介绍你能帮我做什么。

想切换模型时，先退出当前聊天，在终端执行 model use，再重新运行 chat。
本版统一 chat 入口不接受附加命令参数。

建议先在专用工作目录里熟悉操作，不要直接从重要资料目录开始。
safe-mode 不等于禁用所有工具，也不是操作系统沙箱。

## 9. 常见提示与处理

- Initializing agent、Reasoning：初始化或思考过程，等待最终回答。
- 输入框中的英文示例：占位提示，不是必须执行的任务。
- Web search、Browser、tirith 提示：对应可选功能状态，不等于文字对话失败。
- 落后若干提交或提示 hermes update：上游更新提醒。固定版本暂不要自行执行上游更新。
- 401：检查密钥及接口是否匹配。
- 402：检查余额或付款状态。
- 403：检查账号、套餐、模型或接口权限。
- 429：检查请求频率、并发和套餐额度；重新安装通常不能解决。
- 配置已存在：拒绝覆盖。可检查已有配置，或用不同名称建立新配置。
- 权限 600 提示：凭据文件权限不符合要求，不要通过公开文件内容来排查。
- 目录已存在：安装器保护已有目录。保留现场，不要直接删除或强行覆盖。
- EOF、连接超时：保留错误文字及发生步骤，排查网络，不关闭证书验证。

反馈问题时提供操作系统、芯片类型、安装版本、失败步骤及错误文字。
不要提供 API Key、凭据文件、账号密码或含敏感资料的完整日志。

## 10. 当前验证范围

固定安装器：386147344dee20b2921da4afb40c188d6beda499。

六组 CI：
https://github.com/kxz2009-crypto/hermes-cn/actions/runs/37827091899

Ubuntu 24.04、macOS 15 Apple Silicon、macOS 15 Intel 各有 PyPI/TUNA 两组测试。
覆盖安装回归、多模型路由及终端配置。
路由测试使用假密钥，不代表各家真实认证、回复及工具调用通过。

此前另一台 Windows/WSL 电脑的 GLM 专用入口有安装和真实对话成功记录。
本版统一多模型入口仍需分别进行真实服务验证。
尚不承诺全部中国大陆网络、所有实体设备或全部可选功能通过。

参考：
https://learn.microsoft.com/en-us/windows/wsl/install
https://www.python.org/downloads/macos/
