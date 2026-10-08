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
git init -q "$prefix/source"
git -C "$prefix/source" remote add origin \
  https://github.com/NousResearch/hermes-agent.git
git -C "$prefix/source" fetch --depth=1 origin "$commit"
git -C "$prefix/source" checkout --detach FETCH_HEAD
[ "$(git -C "$prefix/source" rev-parse HEAD)" = "$commit" ]

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

# Pinned installation: version output must not wait for update checks.
if [ "$#" -eq 1 ] && [ "$1" = --version ]; then
  exec "$base/venv/bin/python" -I -c \
    'from hermes_cli._startup_fast import print_fast_version_info; print_fast_version_info(check_updates=False)'
fi

exec "$base/venv/bin/hermes" "$@"
LAUNCH
chmod 700 "$prefix/bin/hermes-cn"

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
