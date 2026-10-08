#!/usr/bin/env python3
import getpass
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile

# label, OpenAI-compatible base URL, default model
PRESETS = {
    "glm": (
        "GLM Coding Plan",
        "https://open.bigmodel.cn/api/coding/paas/v4",
        "glm-5.3-flash",
    ),
    "deepseek": (
        "DeepSeek Flash / 按量付费",
        "https://api.deepseek.com",
        "deepseek-flash",
    ),
    "deepseek-pro": (
        "DeepSeek Pro / 按量付费",
        "https://api.deepseek.com",
        "deepseek-v4-pro",
    ),
    "kimi": (
        "Kimi Coding Plan / K3",
        "https://api.kimi.com/coding/v1",
        "k3",
    ),
    "doubao": (
        "豆包 / 火山方舟普通 API",
        "https://ark.cn-beijing.volces.com/api/v3",
        "",
    ),
    "qwen": (
        "Qwen / 百炼北京区普通 API",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "qwen-plus",
    ),
    "minimax": (
        "MiniMax / 按控制台填写接口与模型",
        "",
        "",
    ),
    "mimo": (
        "小米 MiMo",
        "https://api.xiaomimimo.com/v1",
        "mimo-v2.5-pro",
    ),
    "hy3": (
        "腾讯 HY3 / TokenHub",
        "https://tokenhub.tencentmaas.com/v1",
        "hy3",
    ),
    "custom": (
        "自定义 / OpenAI Chat Completions 兼容",
        "",
        "",
    ),
}

class UserInputError(ValueError):
    pass

def fail(message):
    raise UserInputError(message)

def valid_id(value):
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,39}", value):
        fail("配置名称只允许小写字母、数字和短横线，须以字母开头。")
    return value

def validate_values(url, model, key):
    from urllib.parse import urlsplit
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment
            or any(c.isspace() for c in url)):
        fail("Base URL 须为不含账号、查询参数或片段的 HTTPS 地址。")
    if parsed.path.rstrip("/").endswith(("/chat/completions", "/responses", "/messages")):
        fail("请填写 Base URL，不要填写完整请求端点。")
    if not model or len(model) > 200 or any(c.isspace() for c in model):
        fail("模型 ID 不能为空或包含空白。")
    if not key or any(ord(c) < 33 or ord(c) > 126 for c in key):
        fail("API Key 须为非空、无空白的可打印 ASCII 字符。")

def secure_dir(path, create=False):
    if create:
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode)
            or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        fail("模型目录须为当前账号所有、权限 700 的普通目录。")

def secure_read(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "r", encoding="utf-8") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode)
                or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            fail("配置须为当前账号所有、权限 600 的普通文件。")
        return stream.read()

def write_new(path, text):
    fd = os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write(text)

class TerminalIO:
    def __init__(self, reader, writer):
        self.reader = reader
        self.writer = writer

    def readline(self):
        return self.reader.readline()

    def write(self, text):
        return self.writer.write(text)

    def flush(self):
        return self.writer.flush()

def ask(tty, label, default=""):
    suffix = f" [{default}]" if default else ""
    tty.write(f"{label}{suffix}：")
    tty.flush()
    line = tty.readline()
    if not line:
        fail("输入结束，未保存配置。")
    return line.strip() or default

def make_config(name, url, model, key):
    valid_id(name)
    validate_values(url, model, key)
    return {
        "model": {
            "provider": f"custom:{name}",
            "default": model,
            "base_url": url.rstrip("/"),
        },
        "custom_providers": [{
            "name": name,
            "base_url": url.rstrip("/"),
            "model": model,
            "api_key": key,
            "api_mode": "chat_completions",
        }],
    }

def load_profile(store, name):
    valid_id(name)
    home = store / name
    secure_dir(store)
    secure_dir(home)
    data = json.loads(secure_read(home / "config.yaml"))
    entry, = data["custom_providers"]
    if (entry["name"] != name
            or entry["api_mode"] != "chat_completions"
            or data["model"]["provider"] != f"custom:{name}"
            or data["model"]["default"] != entry["model"]
            or data["model"]["base_url"] != entry["base_url"]):
        fail("模型配置结构不一致，请保留文件并检查。")
    validate_values(entry["base_url"], entry["model"], entry["api_key"])
    return home, entry

def selected(store):
    secure_dir(store)
    return valid_id(secure_read(store / "active").strip())

def activate(store, name):
    load_profile(store, name)
    active = store / "active"
    if os.path.lexists(active):
        secure_read(active)
    fd, temporary = tempfile.mkstemp(prefix=".active-", dir=store)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(name + "\n")
        os.replace(temporary, active)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def child_env(root, home):
    # Do not inherit provider keys, profile selectors or arbitrary Hermes overrides.
    allowed = {
        "HOME", "USER", "LOGNAME", "PATH", "LANG", "LC_ALL", "LC_CTYPE",
        "TERM", "COLORTERM", "TZ", "TMPDIR",
        "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
        "http_proxy", "https_proxy", "all_proxy", "no_proxy",
        "SSL_CERT_FILE", "SSL_CERT_DIR", "REQUESTS_CA_BUNDLE",
    }
    env = {k: v for k, v in os.environ.items() if k in allowed}
    env.update(
        HERMES_HOME=str(home),
        HERMES_DISABLE_LAZY_INSTALLS="1",
        PATH=str(root / "venv/bin") + ":" + env.get("PATH", "/usr/bin:/bin"),
    )
    return env

def command_for(root, name, entry):
    return [
        str(root / "venv/bin/hermes"), "chat",
        "--provider", f"custom:{name}",
        "--model", entry["model"],
        "--safe-mode",
    ]

def classify(output):
    status = r"(?:Error\s+code\s*:\s*|HTTP(?:/\d(?:\.\d)?)?\s+|status_code\s*[=:]\s*)"
    rules = [
        (r"\b(?:ModuleNotFoundError|ImportError|FeatureUnavailable)\b", "依赖或可选功能不可用"),
        (status + r"401\b|\bAuthenticationError\b", "认证失败，请核对密钥"),
        (status + r"402\b", "余额或付款状态异常，请检查服务商控制台"),
        (status + r"403\b|\bPermissionDeniedError\b", "账号、模型或套餐访问权限不足"),
        (status + r"429\b|\bRateLimitError\b", "限流或额度限制，请检查套餐及并发"),
        (status + r"(?:400|404)\b|\b(?:BadRequestError|NotFoundError)\b", "接口、模型或请求参数不匹配"),
        (r"\b(?:APITimeoutError|TimeoutError)\b|timed out", "请求超时"),
        (r"\b(?:APIConnectionError|ConnectError)\b", "网络连接失败"),
    ]
    for pattern, message in rules:
        if re.search(pattern, output, re.I):
            return message
    return "未识别的失败或未收到预期回答"

def check(root, name, home, entry):
    expected = "HERMES_CN_MODEL_OK"
    command = command_for(root, name, entry) + [
        "--oneshot", "--quiet", "--max-turns", "1", "--run-budget", "60",
        "--query", f"这是编程助手连通性测试。不要调用工具，只回复：{expected}",
    ]
    print("开始真实对话检查，可能消耗额度；最长约 120 秒。", flush=True)
    process = subprocess.Popen(
        command, env=child_env(root, home), stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", start_new_session=True,
    )
    try:
        output, _ = process.communicate(timeout=120)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        print("FAIL：检查超时或被取消；原始响应不回显。")
        return 1
    matched = any(line.strip() == expected for line in output.splitlines())
    result = {
        "profile": name,
        "status": "PASS" if process.returncode == 0 and matched else "FAIL",
        "exit_code": process.returncode,
        "expected_response_line_found": matched,
    }
    if result["status"] == "FAIL":
        result["diagnostic"] = classify(output)
        result["basis"] = "CLI 文本分类，不是结构化 API 错误解析"
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1

def main():
    os.umask(0o077)
    root = Path(__file__).resolve().parent.parent
    store = root / "state/models"
    args = sys.argv[1:]
    action = args.pop(0) if args else "help"

    if action in ("help", "--help", "-h"):
        print("""Hermes CN 多模型入口
hermes-cn model list
hermes-cn model setup [预设名称] [新配置名称]
hermes-cn model use 配置名称
hermes-cn model status [配置名称]
hermes-cn model check [配置名称]
hermes-cn chat

setup 隐藏输入密钥，不覆盖已有配置。
use/status/list 不发送模型请求；check/chat 会请求模型。
每个配置有独立的密钥、会话和状态目录。
本版接入 OpenAI Chat Completions 兼容接口。
safe-mode 不等于禁用所有工具或操作系统沙箱。""")
        return 0

    if action == "list":
        if args:
            fail("list 不接受额外参数。")
        for name, (label, _, model) in PRESETS.items():
            print(f"{name:14} {label}；模型：{model or '按控制台填写'}")
        if os.path.lexists(store):
            secure_dir(store)
            print("\n已建立的配置目录：")
            for path in sorted(store.iterdir()):
                if not path.name.startswith(".") and path.name != "active":
                    print(path.name)
        return 0

    if action == "setup":
        if len(args) > 2:
            fail("用法：model setup [预设名称] [新配置名称]")
        # A named existing configuration must be rejected before opening a TTY.
        if args:
            if args[0] not in PRESETS:
                fail("未知预设，请运行 model list。")
            requested_name = valid_id(args[1] if len(args) == 2 else args[0])
            if os.path.lexists(store / requested_name):
                fail("配置已存在，拒绝覆盖。可使用另一个新配置名称。")
        with open("/dev/tty", "r", encoding="utf-8") as reader, \
                open("/dev/tty", "w", encoding="utf-8") as writer:
            tty = TerminalIO(reader, writer)
            if args:
                preset = args[0]
            else:
                for name, (label, _, _) in PRESETS.items():
                    tty.write(f"{name}: {label}\n")
                preset = ask(tty, "输入预设名称", "deepseek")
            if preset not in PRESETS:
                fail("未知预设，请运行 model list。")
            name = valid_id(args[1] if len(args) == 2 else preset)
            secure_dir(root / "state", create=True)
            secure_dir(store, create=True)
            home = store / name
            if os.path.lexists(home):
                fail("配置已存在，拒绝覆盖。可使用另一个新配置名称。")
            label, default_url, default_model = PRESETS[preset]
            tty.write(f"\n{label}\n请使用与该接口、地区及套餐匹配的密钥。\n")
            tty.write("Base URL 不要带 /chat/completions；本次不会请求模型。\n")
            url = ask(tty, "Base URL", default_url).rstrip("/")
            model = ask(tty, "模型 ID", default_model)
            key = getpass.getpass("API Key（输入不显示）：", stream=tty)
            config = make_config(name, url, model, key)
        home.mkdir(mode=0o700)
        write_new(home / "config.yaml", json.dumps(config, ensure_ascii=False, indent=2) + "\n")
        print(f"配置保存成功：{name}。权限 600，未发送请求。")
        print(f"下一步：hermes-cn model use {name}")
        return 0

    if action == "use":
        if len(args) != 1:
            fail("用法：model use 配置名称")
        activate(store, args[0])
        print(f"当前模型配置：{args[0]}。仅影响之后通过此入口启动的会话。")
        return 0

    if action not in ("status", "check", "chat"):
        fail("未知命令，请运行 hermes-cn model --help。")
    if len(args) > 1 or (action == "chat" and args):
        fail("status/check 最多指定一个配置；本版 chat 不接受额外参数。")
    name = args[0] if args else selected(store)
    home, entry = load_profile(store, name)

    if action == "status":
        print(f"配置：{name}\n接口：{entry['base_url']}\n模型：{entry['model']}")
        print("PASS：本地配置、权限和所有者检查通过；不代表 API 对话通过。")
        return 0
    if action == "check":
        return check(root, name, home, entry)
    command = command_for(root, name, entry)
    os.execve(command[0], command, child_env(root, home))

if __name__ == "__main__":
    try:
        sys.exit(main())
    except UserInputError as exc:
        print("操作失败：" + str(exc), file=sys.stderr)
        sys.exit(2)
    except (ValueError, OSError, KeyError, TypeError):
        print("操作失败：请检查命令、配置、文件权限或目标是否已存在。", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\n操作取消。", file=sys.stderr)
        sys.exit(130)
