#!/usr/bin/env bash
set -euo pipefail
umask 077

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

prefix=''
uv=''
source_name=tuna
intel_wheel=''

while [ "$#" -gt 0 ]; do
  case "$1" in
    --prefix|--uv|--source|--intel-wheel)
      [ "$#" -ge 2 ] || fail "Missing value for $1"
      case "$1" in
        --prefix) prefix="$2" ;;
        --uv) uv="$2" ;;
        --source) source_name="$2" ;;
        --intel-wheel) intel_wheel="$2" ;;
      esac
      shift 2
      ;;
    --help)
      echo 'Usage: bash install-lite.sh --prefix /new/absolute/path --uv /path/to/uv [--source tuna|pypi] [--intel-wheel /path/to/wheel]'
      exit 0
      ;;
    *) fail "Unknown argument: $1" ;;
  esac
done

case "$prefix" in
  /*) ;;
  *) fail '--prefix must be an absolute path' ;;
esac
case "$prefix" in
  /|*/|*/../*|*/./*|*/..|*/.) fail 'Invalid installation path' ;;
esac
case "$prefix" in
  *[[:space:]]*) fail 'This experimental installer requires a path without whitespace' ;;
esac
[ ! -e "$prefix" ] && [ ! -L "$prefix" ] ||
  fail 'Installation target already exists; refusing to overwrite'

case "$uv" in /*) ;; *) fail '--uv must be an absolute path' ;; esac
[ -x "$uv" ] || fail 'uv executable not found'
uv_version=$("$uv" --version)
case "$uv_version" in
  'uv 0.12.23'|'uv 0.12.23 '*) ;;
  *) fail "Expected uv 0.12.23, found: $uv_version" ;;
esac

command -v git >/dev/null || fail 'git is required'
os=$(uname -s)
arch=$(uname -m)
case "$os/$arch" in
  Linux/x86_64|Darwin/arm64|Darwin/x86_64) ;;
  *) fail "Untested platform: $os/$arch" ;;
esac
if [ "$os" = Darwin ]; then
  mac_version=$(sw_vers -productVersion)
  [ "${mac_version%%.*}" = 15 ] ||
    fail 'This experimental release is limited to macOS 15'
fi
if [ "$os/$arch" = Darwin/x86_64 ] && [ -n "$intel_wheel" ]; then
  [ -f "$intel_wheel" ] || fail 'Local Intel wheel not found'
  case "$intel_wheel" in
    /*/cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl) ;;
    *) fail 'Unexpected Intel wheel path or filename' ;;
  esac
  actual=$(shasum -a 256 "$intel_wheel")
  actual=${actual%% *}
  [ "$actual" = 11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f ] ||
    fail 'Intel wheel hash mismatch'
fi

case "$source_name" in
  tuna) index=https://pypi.tuna.tsinghua.edu.cn/simple ;;
  pypi) index=https://pypi.org/simple ;;
  *) fail 'Source must be tuna or pypi' ;;
esac

if [ "$os/$arch" = Darwin/x86_64 ] && [ -z "$intel_wheel" ]; then
  command -v curl >/dev/null || fail 'curl is required for Intel bundle download'
  command -v unzip >/dev/null || fail 'unzip is required for Intel bundle download'
  command -v shasum >/dev/null || fail 'shasum is required for Intel bundle verification'
fi

# All installer-managed data is kept under the requested new directory.
mkdir -p "$prefix"
prefix=$(cd "$prefix" && pwd -P)
trap 'printf "Installation stopped. Diagnostic files retained at: %s\n" "$prefix" >&2' ERR
mkdir -p "$prefix/config" "$prefix/cache" "$prefix/python" \
  "$prefix/state" "$prefix/bin" "$prefix/wheels" "$prefix/work"

unset UV_CONFIG_FILE UV_INDEX UV_INDEX_URL UV_EXTRA_INDEX_URL UV_DEFAULT_INDEX
unset UV_PYTHON UV_PYTHON_INSTALL_DIR UV_PROJECT_ENVIRONMENT
unset PIP_INDEX_URL PIP_EXTRA_INDEX_URL PYTHONPATH PYTHONHOME
unset HERMES_NIX_BUILD
export UV_NO_CONFIG=1
export UV_CACHE_DIR="$prefix/cache"
export UV_PYTHON_INSTALL_DIR="$prefix/python"
export UV_PROJECT_ENVIRONMENT="$prefix/venv"
export XDG_CONFIG_HOME="$prefix/config"
export XDG_CONFIG_DIRS="$prefix/config"
export PIP_CONFIG_FILE=/dev/null

commit=f97608f178d1ffeca59860195ab7da295f7c8e5f
# CN_SOURCE_DOWNLOAD_BEGIN
command -v curl >/dev/null || {
  echo '缺少 curl，请先安装 curl。' >&2
  exit 1
}
command -v python3 >/dev/null || {
  echo '缺少 python3，请先完成准备步骤。' >&2
  exit 1
}

source_dir="$prefix/work/source-download"
mkdir -p "$source_dir"
source_archive="hermes-source-$commit.tar.gz"
source_url="https://hermes.localvram.cn/downloads/hermes-source/$commit/$source_archive"
source_hash=c6a92c0e9d06f69714e4b194584891a6c27e45870ad40f4a3db1293db6cd9b58

echo '从 LocalVRAM 腾讯云下载固定版本 Hermes 源码……'
# CN_SOURCE_FETCH_BEGIN
source_started=$SECONDS
source_rc=1
for source_attempt in 1 2 3; do
  source_remaining=$((1200 - (SECONDS - source_started)))
  if [ "$source_remaining" -le 0 ]; then
    echo 'STOP：源码下载超过总时间限制。' >&2
    exit 28
  fi

  printf '源码下载尝试：%s/3；本次最多 %s 秒\n' \
    "$source_attempt" "$source_remaining"

  # 每次重新覆盖文件，避免把残缺响应拼接进下一次下载。
  if curl -q --fail --silent --show-error --location \
    --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time "$source_remaining" \
    --speed-limit 1024 --speed-time 60 --retry 0 \
    "$source_url" |
    cat > "$source_dir/$source_archive"
  then
    source_rc=0
    break
  else
    source_rc=$?
  fi

  printf '源码下载未完成，退出码：%s\n' "$source_rc" >&2
  case "$source_rc" in
    6|7|18|28|35|52|55|56|92) ;;
    *) exit "$source_rc" ;;
  esac

  if [ "$source_attempt" -lt 3 ]; then
    echo '等待 3 秒后重新下载……' >&2
    sleep 3
  fi
done

if [ "$source_rc" -ne 0 ]; then
  echo 'STOP：源码下载重试仍失败，保留诊断文件。' >&2
  exit "$source_rc"
fi
# CN_SOURCE_FETCH_END

python3 - "$source_dir/$source_archive" "$source_hash" \
  "$source_dir/extracted" << 'CN_SOURCE_VERIFY_END'
import hashlib
from pathlib import Path, PurePosixPath
import shutil
import sys
import tarfile

archive, expected, destination = sys.argv[1:]
digest = hashlib.sha256()
with open(archive, "rb") as stream:
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(chunk)
if digest.hexdigest() != expected:
    sys.exit("STOP：源码包 SHA256 不匹配，未解包。")

root = Path(destination)
if root.exists() or root.is_symlink():
    sys.exit("STOP：源码恢复目录已存在，不覆盖。")

with tarfile.open(archive, "r:gz") as package:
    members = package.getmembers()
    seen = set()
    total = 0
    for member in members:
        path = PurePosixPath(member.name)
        if (
            path.is_absolute()
            or ".." in path.parts
            or not path.parts
            or path.parts[0] != "upstream.git"
            or not (member.isdir() or member.isfile())
            or str(path) in seen
        ):
            sys.exit("STOP：源码包包含非预期路径或文件类型。")
        seen.add(str(path))
        total += member.size
    if not members or total > 1024 * 1024 * 1024:
        sys.exit("STOP：源码包内容为空或大小异常。")

    root.mkdir(mode=0o700)
    for member in members:
        target = root.joinpath(*PurePosixPath(member.name).parts)
        if member.isdir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
        else:
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with package.extractfile(member) as source:
                with target.open("xb") as output:
                    shutil.copyfileobj(source, output)
            target.chmod(0o600)

print("PASS：源码包哈希、路径及文件类型校验")
CN_SOURCE_VERIFY_END

source_repo="$source_dir/extracted/upstream.git"
[ "$(git --git-dir="$source_repo" rev-parse HEAD)" = "$commit" ]
git --git-dir="$source_repo" fsck --full

git init -q "$prefix/source"
git -C "$prefix/source" remote add origin \
  https://github.com/NousResearch/hermes-agent.git
git -c protocol.file.allow=always -C "$prefix/source" \
  fetch --depth=1 --update-shallow "$source_repo" \
  refs/heads/pinned
[ "$(git -C "$prefix/source" rev-parse FETCH_HEAD)" = "$commit" ]
git -C "$prefix/source" checkout --detach FETCH_HEAD
[ "$(git -C "$prefix/source" rev-parse HEAD)" = "$commit" ]
echo 'PASS：固定版本源码已从本地分发包恢复'
# CN_SOURCE_DOWNLOAD_END

"$uv" python install --no-bin 3.11.17
"$uv" venv --managed-python --python 3.11.17 "$prefix/venv"
python="$prefix/venv/bin/python"

if [ "$os/$arch" = Darwin/x86_64 ] && [ -z "$intel_wheel" ]; then
  bundle_dir="$prefix/work/intel-bundle"
  mkdir -p "$bundle_dir"
  bundle_name=cryptography-50.0.0-macos15-intel-r2-bundle.zip
  bundle_url="https://github.com/kxz2009-crypto/hermes-cn/releases/download/deps-cryptography-50.0.0-macos15-intel-r2/$bundle_name"

  curl -q --fail --silent --show-error --location \
    --proto '=https' --proto-redir '=https' \
    --connect-timeout 15 --max-time 300 \
    --retry 3 --retry-delay 5 \
    "$bundle_url" |
    cat > "$bundle_dir/$bundle_name"

  (
    cd "$bundle_dir"
    echo '6f751a5ace4892baabb292f357e9c8a587e11960e6d22634d37611565e6cde96  cryptography-50.0.0-macos15-intel-r2-bundle.zip' |
      shasum -a 256 -c -
  )

  # ZIP 整体校验通过后，只读取明确列出的文件，不执行通用解压。
  for bundled_file in \
    cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl \
    build-inputs.json toolchain.txt INTEGRATION_ACCEPTANCE.md \
    THIRD_PARTY_NOTICES.draft.txt SHA256SUMS README.txt
  do
    unzip -p "$bundle_dir/$bundle_name" "$bundled_file" |
      cat > "$bundle_dir/$bundled_file"
    test -s "$bundle_dir/$bundled_file"
  done

  (
    cd "$bundle_dir"
    echo '11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f  cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl' |
      shasum -a 256 -c -
  )
  intel_wheel="$bundle_dir/cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl"
fi

(
  cd "$prefix/source"
  unset UV_NO_CONFIG
  "$uv" export --locked --format requirements-txt \
    --no-default-groups --no-emit-project --no-header --no-annotate \
    --output-file "$prefix/work/core-original.txt"
)
grep -q -- '--hash=sha256:' "$prefix/work/core-original.txt"
if grep -nE 'https?://|git\+|file:|^-e |^--.*index|^--find-links' \
  "$prefix/work/core-original.txt"; then
  fail 'Unexpected source override in requirements'
fi
cat "$prefix/work/core-original.txt" > "$prefix/work/core-install.txt"

if [ "$os/$arch" = Darwin/x86_64 ]; then
  wheel_name=cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl
  cat "$intel_wheel" > "$prefix/wheels/$wheel_name"
  "$python" - "$prefix" << 'PY' |
import hashlib, pathlib, re, sys
root = pathlib.Path(sys.argv[1])
wheel = root / "wheels/cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl"
digest = "11504d18f54d3435a799f70febb3001b1efbab30d6d05570e447d4c571318a6f"
assert hashlib.sha256(wheel.read_bytes()).hexdigest() == digest
text = (root / "work/core-original.txt").read_text()
pattern = r"(?m)^cryptography==50\.0\.0[^\n]*(?:\n[ \t]+[^\n]*)*"
matches = list(re.finditer(pattern, text))
assert len(matches) == 1
block = matches[0].group()
assert block.splitlines()[0].split("\\", 1)[0].strip() == "cryptography==50.0.0"
assert "--hash=sha256:" in block
replacement = f"cryptography @ {wheel.as_uri()} --hash=sha256:{digest}"
print(re.sub(pattern, lambda _: replacement, text), end="")
PY
    cat > "$prefix/work/core-install.txt"
fi

cd "$prefix/work"
"$uv" pip sync core-install.txt --python "$python" \
  --default-index "$index" --require-hashes --only-binary=:all:

cat > "$prefix/work/build-constraints.txt" << 'BUILD'
setuptools==83.0.0
wheel==0.48.0
packaging==26.3
BUILD

"$uv" pip install --python "$python" --default-index "$index" \
  --build-constraint "$prefix/work/build-constraints.txt" \
  --no-deps --editable "$prefix/source"
"$uv" pip check --python "$python"
git -C "$prefix/source" diff --exit-code HEAD -- pyproject.toml uv.lock

cat > "$prefix/bin/hermes-cn" << 'LAUNCH'
#!/usr/bin/env bash
set -euo pipefail
base=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
unset PYTHONPATH PYTHONHOME HERMES_LAZY_INSTALL_TARGET
export HERMES_DISABLE_LAZY_INSTALLS=1
export HERMES_HOME="$base/state"
export PATH="$base/venv/bin:$PATH"

# Explicit model management; preserve legacy chat until a model is selected.
if [ "${1:-}" = model ]; then
  shift
  exec "$base/venv/bin/python" -I "$base/bin/hermes-model.py" "$@"
fi
if [ "${1:-}" = chat ] && {
  [ -e "$base/state/models/active" ] || [ -L "$base/state/models/active" ];
}; then
  shift
  exec "$base/venv/bin/python" -I "$base/bin/hermes-model.py" chat "$@"
fi

# Pinned installation: version output must not wait for update checks.
if [ "$#" -eq 1 ] && [ "$1" = --version ]; then
  exec "$base/venv/bin/python" -I -c \
    'from hermes_cli._startup_fast import print_fast_version_info; print_fast_version_info(check_updates=False)'
fi

exec "$base/venv/bin/hermes" "$@"
LAUNCH
chmod 700 "$prefix/bin/hermes-cn"

mkdir -p "$prefix/bin" "$prefix/state"
cat > "$prefix/bin/hermes-model.py" << 'CN_MODEL_PY_END'
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
CN_MODEL_PY_END
chmod 700 "$prefix/bin/hermes-model.py"
"$prefix/bin/hermes-cn" model --help

mkdir -p "$prefix/bin" "$prefix/state"
cat > "$prefix/bin/hermes-glm" << 'GLM_LAUNCH_END'
#!/usr/bin/env bash
set -euo pipefail
set +x
umask 077

base=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)
credentials="$base/state/glm-coding.env"
unset PYTHONPATH PYTHONHOME HERMES_LAZY_INSTALL_TARGET
export HERMES_DISABLE_LAZY_INSTALLS=1
export HERMES_HOME="$base/state"

usage() {
  cat << 'HELP'
Hermes CN · 国内 GLM Coding Plan
用法：hermes-glm setup|status|check|chat

setup   隐藏输入并保存密钥；已有凭据不覆盖
status  本地检查配置，不发送请求
check   发送简短对话检查，可能消耗套餐额度
chat    开始交互对话；可追加 Hermes chat 参数

固定接口：https://open.bigmodel.cn/api/coding/paas/v4
固定默认模型：glm-5.3-flash
对话启用 safe-mode；这不等同于禁用所有工具或操作系统沙箱。
HELP
}

action=${1:---help}
[ "$#" -eq 0 ] || shift
case "$action" in
  --help|-h|help) usage; exit 0 ;;
  setup|status|check)
    [ "$#" -eq 0 ] || {
      echo '此命令不接受额外参数。' >&2
      exit 2
    }
    ;;
  chat) ;;
  *) usage >&2; exit 2 ;;
esac

test -d "$base/state" && test ! -L "$base/state" &&
test -O "$base/state" || {
  echo '请以安装所属账号运行；状态目录须为普通目录。' >&2
  exit 2
}

if [ "$action" = setup ]; then
  if [ -e "$credentials" ] || [ -L "$credentials" ]; then
    echo '凭据已存在，未覆盖。可运行 hermes-glm status 检查。' >&2
    exit 2
  fi
  printf '国内 GLM Coding Plan API Key（输入不显示）：' >/dev/tty
  IFS= read -r -s key </dev/tty
  printf '\n' >/dev/tty
  [[ "$key" =~ ^[A-Za-z0-9._-]+$ ]] || {
    unset key
    echo '密钥为空或含非预期字符，未保存。' >&2
    exit 2
  }
  mkdir -p "$base/state"
  (
    set -o noclobber
    echo "GLM_API_KEY=$key" > "$credentials"
  )
  unset key
  echo '配置已保存，权限为 600。本次没有发送请求。'
  echo '下一步：hermes-glm status；需要联网验证时运行 hermes-glm check。'
  exit 0
fi

if [ ! -f "$credentials" ] || [ -L "$credentials" ]; then
  echo '尚未配置或凭据文件类型不正确，请先运行 hermes-glm setup。' >&2
  exit 2
fi

if [ "$action" = status ]; then
  exec "$base/venv/bin/python" -I "$base/bin/hermes-glm.py" --status
elif [ "$action" = check ]; then
  exec "$base/venv/bin/python" -I "$base/bin/hermes-glm.py" --check
else
  exec "$base/venv/bin/python" -I "$base/bin/hermes-glm.py" "$@"
fi
GLM_LAUNCH_END
cat > "$prefix/bin/hermes-glm.py" << 'GLM_PY_END'
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

from dotenv import dotenv_values

root = Path(__file__).resolve().parent.parent
credential_file = root / "state/glm-coding.env"
try:
    info = credential_file.lstat()
except OSError:
    sys.exit("无法读取凭据文件，请运行 hermes-glm setup 或检查权限。")
if not stat.S_ISREG(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o600:
    sys.exit("凭据文件必须为权限 600 的普通文件。")
if info.st_uid != os.geteuid():
    sys.exit("请以安装所属账号运行。")

key = dotenv_values(credential_file, interpolate=False).get("GLM_API_KEY")
if not key:
    sys.exit("凭据文件缺少 GLM_API_KEY。")

if sys.argv[1:] == ["--status"]:
    print("PASS：独立凭据文件、权限、所有者及密钥字段检查通过。")
    print("接口：https://open.bigmodel.cn/api/coding/paas/v4")
    print("模型：glm-5.3-flash")
    print("本地配置检查不代表密钥有效或服务可用；未发送请求。")
    sys.exit(0)

endpoint = "https://open.bigmodel.cn/api/coding/paas/v4"
model = "glm-5.3-flash"
env = dict(os.environ)
env.update(
    GLM_API_KEY=key,
    GLM_BASE_URL=endpoint,
    HERMES_HOME=str(root / "state"),
)
for name in ("ZAI_API_KEY", "Z_AI_API_KEY", "PYTHONPATH", "PYTHONHOME"):
    env.pop(name, None)

command = [
    str(root / "bin/hermes-cn"), "chat",
    "--provider", "zai",
    "--model", model,
    "--safe-mode",
]

if sys.argv[1:] != ["--check"]:
    os.execve(command[0], command + sys.argv[1:], env)

expected = "HERMES_GLM_OK"
command += [
    "--oneshot", "--quiet", "--max-turns", "1",
    "--run-budget", "60",
    "--query", f"这是编程助手接入测试。不要调用工具，只回复：{expected}",
]
summary = {
    "test": "installed Hermes CLI connection check",
    "endpoint_configured": endpoint,
    "model_requested": model,
    "status": "FAIL",
}
def classify_cli_failure(output):
    import re

    # 数字状态码需要明确的 HTTP/错误码上下文。
    status = (
        r"(?:Error\s+code\s*:\s*|"
        r"HTTP(?:/\d(?:\.\d)?)?\s+|"
        r"HTTP\s+(?:Error|status)\s*:?\s*|"
        r"status_code\s*[=:]\s*)"
    )
    rules = [
        (
            "dependency",
            r"\b(?:ModuleNotFoundError|ImportError|FeatureUnavailable)\b",
            "缺少依赖或可选功能不可用。请保留诊断记录，勿反复重试模型请求。",
        ),
        (
            "rate_limit",
            status + r"429\b|\bRateLimitError\b|too many requests",
            "服务返回限流或额度限制。请检查 Coding Plan 额度和并发使用情况，稍后再试。",
        ),
        (
            "authentication",
            status + r"401\b|\bAuthenticationError\b|invalid.api.key|unauthorized",
            "认证失败。请检查此安装配置的 API Key 是否有效。",
        ),
        (
            "permission",
            status + r"403\b|\bPermissionDeniedError\b|forbidden",
            "访问被拒绝。请检查账号、套餐及模型访问权限。",
        ),
        (
            "timeout",
            r"\b(?:APITimeoutError|TimeoutError)\b|timed out",
            "请求超时。请检查网络和代理配置，稍后再试。",
        ),
        (
            "connection",
            r"\b(?:APIConnectionError|ConnectError)\b|connection refused|"
            r"name resolution|certificate verify failed",
            "连接失败。请检查网络、DNS、代理和证书配置。",
        ),
        (
            "request_rejected",
            status + r"(?:400|404)\b|\b(?:BadRequestError|NotFoundError)\b",
            "请求被拒绝或目标不存在。请核对接口地址、模型名称及请求参数。",
        ),
    ]
    for code, pattern, message in rules:
        if re.search(pattern, output, re.I):
            return {
                "category": code,
                "message": message,
                "classification_basis": "CLI output pattern; not a structured API error",
            }
    return {
        "category": "unknown",
        "message": "CLI 未成功完成对话，需要进一步诊断；原始响应不在此处显示。",
        "classification_basis": "no recognized CLI error pattern",
    }

started = time.monotonic()
process = None
try:
    process = subprocess.Popen(
        command, env=env, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, start_new_session=True,
    )
    output, _ = process.communicate(timeout=120)
    matched = any(line.strip() == expected for line in output.splitlines())
    summary.update(
        exit_code=process.returncode,
        expected_response_line_found=matched,
    )
    if process.returncode == 0 and matched:
        summary["status"] = "PASS"
        summary["response"] = expected
    else:
        # 不打印原始输出，避免错误响应意外包含凭据。
        summary["reason"] = "CLI failed or expected reply missing"
        summary["diagnostic"] = classify_cli_failure(output)
except subprocess.TimeoutExpired:
    os.killpg(process.pid, signal.SIGKILL)
    process.communicate()
    summary["reason"] = "CLI exceeded 120 seconds"
except Exception as exc:
    summary["error_type"] = type(exc).__name__

summary["elapsed_seconds"] = round(time.monotonic() - started, 2)
print(json.dumps(summary, ensure_ascii=False, indent=2))
sys.exit(0 if summary["status"] == "PASS" else 1)
GLM_PY_END

chmod 700 "$prefix/bin/hermes-glm" "$prefix/bin/hermes-glm.py"
"$prefix/bin/hermes-glm" --help
"$python" - "$prefix/bin/hermes-glm.py" << 'GLM_SYNTAX_END'
import pathlib, sys
compile(pathlib.Path(sys.argv[1]).read_text(), sys.argv[1], "exec")
GLM_SYNTAX_END

"$python" - "$prefix" << 'PY'
import importlib.metadata as metadata
import pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
assert metadata.version("hermes-agent") == "0.21.5"
for option in ("--help", "--version"):
    result = subprocess.run(
        [str(root / "bin/hermes-cn"), option],
        cwd=root / "work", stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=60,
    )
    print(result.stdout)
    assert result.returncode == 0, (option, result.returncode)
    assert result.stdout.strip()
    if option == "--help":
        assert "usage:" in result.stdout.lower()
print("PASS: experimental installer CLI smoke test")
PY

echo "$commit" > "$prefix/UPSTREAM_COMMIT"
echo 'experimental-lite-0.1' > "$prefix/INSTALL_COMPLETE"
trap - ERR
printf '\nInstalled experimental CLI: %s/bin/hermes-cn\n' "$prefix"
printf 'State directory: %s/state\n' "$prefix"

printf 'Configure GLM: %s/bin/hermes-glm setup\n' "$prefix"
printf 'Check GLM: %s/bin/hermes-glm check\n' "$prefix"
printf 'Start GLM chat: %s/bin/hermes-glm chat\n' "$prefix"
