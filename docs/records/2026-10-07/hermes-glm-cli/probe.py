import json
import os
import pathlib
import subprocess
import sys
import time
from datetime import datetime, timezone
from dotenv import dotenv_values

prefix = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path(sys.argv[2]).resolve()
summary = {
    "time_utc": datetime.now(timezone.utc).isoformat(),
    "test": "Installer-generated hermes-cn CLI",
    "model": "glm-5.3-flash",
    "endpoint": "https://open.bigmodel.cn/api/coding/paas/v4",
    "status": "FAIL",
}
started = time.monotonic()

try:
    credentials = pathlib.Path.home() / ".hermes/.env"
    if not credentials.is_file():
        raise RuntimeError("Credential file missing")
    values = dotenv_values(credentials, interpolate=False)
    key = values.get("GLM_API_KEY")
    del values
    if not key or not key.strip():
        raise RuntimeError("GLM_API_KEY missing")

    child_env = {
        "HOME": str(pathlib.Path.home()),
        "PATH": "/usr/bin:/bin",
        "LANG": "C.UTF-8",
        "GLM_API_KEY": key,
        "GLM_BASE_URL": summary["endpoint"],
    }
    command = [
        str(prefix / "bin/hermes-cn"),
        "chat",
        "--provider", "zai",
        "--model", summary["model"],
        "--safe-mode",
        "--oneshot",
        "--quiet",
        "--max-turns", "1",
        "--run-budget", "60",
        "--query",
        "这是编程助手CLI接入测试。不调用任何工具，只回复：HERMES_CLI_GLM_OK",
    ]
    result = subprocess.run(
        command,
        cwd=work,
        env=child_env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=120,
    )
    output = result.stdout.replace(key, "[REDACTED]")
    marker_found = any(
        line.strip() == "HERMES_CLI_GLM_OK"
        for line in output.splitlines()
    )
    summary.update({
        "exit_code": result.returncode,
        "expected_response_line_found": marker_found,
        "output_tail": output[-10000:],
        "status": "REVIEW" if result.returncode == 0 else "FAIL",
    })
except subprocess.TimeoutExpired:
    summary["error_type"] = "TimeoutExpired"
except Exception as exc:
    summary["error_type"] = type(exc).__name__
finally:
    summary["elapsed_seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
