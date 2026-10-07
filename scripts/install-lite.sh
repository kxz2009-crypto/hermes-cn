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
if [ "$os/$arch" = Darwin/x86_64 ]; then
  [ -f "$intel_wheel" ] || fail '--intel-wheel is required on Intel Mac'
  case "$intel_wheel" in
    /*/cryptography-50.0.0-cp311-abi3-macosx_15_0_x86_64.whl) ;;
    *) fail 'Unexpected Intel wheel path or filename' ;;
  esac
  actual=$(shasum -a 256 "$intel_wheel")
  actual=${actual%% *}
  [ "$actual" = bb6320d4dc523339041c40e58176beb3235d59c133968490694fd1924c68c49c ] ||
    fail 'Intel wheel hash mismatch'
fi

case "$source_name" in
  tuna) index=https://pypi.tuna.tsinghua.edu.cn/simple ;;
  pypi) index=https://pypi.org/simple ;;
  *) fail 'Source must be tuna or pypi' ;;
esac

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
digest = "bb6320d4dc523339041c40e58176beb3235d59c133968490694fd1924c68c49c"
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
unset PYTHONPATH PYTHONHOME
export HERMES_HOME="$base/state"
export PATH="$base/venv/bin:$PATH"
exec "$base/venv/bin/hermes" "$@"
LAUNCH
chmod 700 "$prefix/bin/hermes-cn"

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
