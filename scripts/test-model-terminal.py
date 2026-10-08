#!/usr/bin/env python3
import errno
import json
import os
from pathlib import Path
import pty
import select
import signal
import stat
import subprocess
import sys
import tempfile
import termios
import time

os.umask(0o077)
installer = Path(sys.argv[1]).resolve()
venv = Path(sys.argv[2]).resolve()
assert (venv / "bin/python").is_file()
text = installer.read_text()
secret = "HERMES_OFFLINE_TEST_ONLY"

def extract(start, end):
    assert text.count(start) == 1
    return text.split(start, 1)[1].split(end, 1)[0] + "\n"

with tempfile.TemporaryDirectory(prefix="hermes-cn-terminal-") as directory:
    root = Path(directory)
    (root / "bin").mkdir(mode=0o700)
    (root / "state").mkdir(mode=0o700)
    (root / "venv").symlink_to(venv, target_is_directory=True)

    launcher = root / "bin/hermes-cn"
    helper = root / "bin/hermes-model.py"
    launcher.write_text(extract(
        'cat > "$prefix/bin/hermes-cn" << \'LAUNCH\'\n', "\nLAUNCH\n"))
    helper.write_text(extract(
        'cat > "$prefix/bin/hermes-model.py" << \'CN_MODEL_PY_END\'\n',
        "\nCN_MODEL_PY_END\n"))
    launcher.chmod(0o700)
    helper.chmod(0o700)

    env = {
        "HOME": str(root),
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "LANG": "en_US.UTF-8",
        "PYTHONUTF8": "1",
        "TERM": "dumb",
    }

    pid, master = pty.fork()
    if pid == 0:
        os.chdir(root)
        os.execve(str(launcher), [
            str(launcher), "model", "setup", "deepseek"
        ], env)

    output = bytearray()
    prompts = [
        ("Base URL [".encode(), b"\n"),
        ("模型 ID [".encode(), b"\n"),
        ("API Key（输入不显示）：".encode(), (secret + "\n").encode()),
    ]
    index = 0
    cursor = 0
    status = None
    deadline = time.monotonic() + 30
    try:
        while True:
            if time.monotonic() >= deadline:
                raise AssertionError("terminal_interaction_timeout")
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    chunk = b""
                output.extend(chunk)

                if index < len(prompts):
                    prompt, response = prompts[index]
                    position = output.find(prompt, cursor)
                    if position >= 0:
                        if index == 2:
                            flags = termios.tcgetattr(master)[3]
                            assert not flags & termios.ECHO, "secret_input_echo_enabled"
                        os.write(master, response)
                        cursor = len(output)
                        index += 1

            found, child_status = os.waitpid(pid, os.WNOHANG)
            if found:
                status = child_status
                break

        # Drain bytes already written before checking for accidental key echo.
        while select.select([master], [], [], 0)[0]:
            try:
                chunk = os.read(master, 65536)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    break
                raise
            if not chunk:
                break
            output.extend(chunk)

        assert index == 3, "missing_interactive_prompt"
        assert os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0, "setup_failed"
        assert secret.encode() not in output, "secret_echoed"
    finally:
        if status is None:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
        os.close(master)

    path = root / "state/models/deepseek/config.yaml"
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode)
    assert stat.S_IMODE(info.st_mode) == 0o600
    assert info.st_uid == os.geteuid()
    entry, = json.loads(path.read_text())["custom_providers"]
    assert entry["api_key"] == secret
    assert entry["base_url"] == "https://api.deepseek.com"
    assert entry["model"] == "deepseek-flash"

    def run(*args, expected=0):
        result = subprocess.run(
            [str(launcher), "model", *args],
            env=env, cwd=root, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", timeout=15,
        )
        assert result.returncode == expected, "unexpected_exit_code"
        assert secret not in result.stdout, "secret_in_output"
        return result.stdout

    run("use", "deepseek")
    run("status")
    before = path.read_bytes()
    message = run("setup", "deepseek", expected=2)
    assert "配置已存在" in message, "missing_existing_config_message"
    assert path.read_bytes() == before

    path.chmod(0o644)
    message = run("status", expected=2)
    assert "权限 600" in message, "missing_permission_message"
    path.chmod(0o600)
    run("status")

print("PASS：伪终端首次配置、关闭密钥回显、默认值、权限、切换及具体错误提示")
print("范围：假密钥，未执行 check/chat，未发送模型请求")
