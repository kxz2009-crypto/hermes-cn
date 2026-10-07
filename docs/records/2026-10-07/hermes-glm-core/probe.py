import contextlib
import io
import json
import pathlib
import sys
import time
from datetime import datetime, timezone
from dotenv import dotenv_values

prefix = pathlib.Path(sys.argv[1]).resolve()
work = pathlib.Path.cwd()
endpoint = "https://open.bigmodel.cn/api/coding/paas/v4"
summary = {
    "time_utc": datetime.now(timezone.utc).isoformat(),
    "test": "Hermes Agent core; not CLI end-to-end",
    "model": "glm-5.3-flash",
    "endpoint": endpoint,
    "status": "FAIL",
}
captured = io.StringIO()
started = time.monotonic()

try:
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        credential_file = pathlib.Path.home() / ".hermes/.env"
        if not credential_file.is_file():
            raise RuntimeError("Credential file missing")
        values = dotenv_values(credential_file, interpolate=False)
        key = values.get("GLM_API_KEY")
        del values
        if not key or not key.strip():
            raise RuntimeError("GLM_API_KEY missing")

        import run_agent
        assert pathlib.Path(run_agent.__file__).resolve() == (
            prefix / "source/run_agent.py"
        ), "Unexpected Hermes source"

        agent = run_agent.AIAgent(
            model="glm-5.3-flash",
            provider="zai",
            base_url=endpoint,
            api_key=key,
            enabled_toolsets=[],
            max_iterations=2,
            max_tokens=1024,
            run_budget_seconds=90,
            save_trajectories=False,
            verbose_logging=False,
            quiet_mode=True,
            skip_context_files=True,
            load_soul_identity=False,
            skip_memory=True,
            skip_background_review=True,
            checkpoints_enabled=False,
            cwd=str(work),
        )

        assert agent.enabled_toolsets == [], "Toolset selection changed"
        assert isinstance(agent.tools, list), "Unexpected tools representation"
        assert len(agent.tools) == 0, "Non-empty tool list; request blocked"
        summary["tools_before_request"] = 0

        answer = agent.run_conversation(
            user_message="这是编程助手接入测试。请只回复：HERMES_GLM_OK",
            system_message="只回答本次接入测试，不调用工具。"
        )

        assert isinstance(answer, dict), "Unexpected response envelope"
        summary["result_keys"] = sorted(str(k) for k in answer)
        final = answer.get("final_response")
        summary["tools_after_request"] = len(agent.tools)
        messages = answer.get("messages") or []
        has_tool_calls = any(
            isinstance(message, dict) and message.get("tool_calls")
            for message in messages
        )
        summary["tool_calls_present"] = has_tool_calls
        if isinstance(final, str):
            summary["response"] = final.replace(key, "[REDACTED]")
        summary["agent_error_present"] = bool(answer.get("error"))
        summary["status"] = (
            "PASS"
            if isinstance(final, str)
            and final.strip() == "HERMES_GLM_OK"
            and not answer.get("error")
            and not has_tool_calls
            and len(agent.tools) == 0
            else "REVIEW"
        )
except Exception as exc:
    summary["error_type"] = type(exc).__name__
    # 不输出异常正文或捕获日志，避免泄露凭据。
finally:
    summary["elapsed_seconds"] = round(time.monotonic() - started, 2)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
