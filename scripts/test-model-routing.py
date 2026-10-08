#!/usr/bin/env python3
"""Offline route verification against the installed, pinned Hermes runtime."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def deny_network(event, args):
    if event in {
        "socket.connect", "socket.connect_ex",
        "socket.getaddrinfo", "socket.gethostbyname",
        "socket.gethostbyaddr", "socket.sendto",
        "subprocess.Popen", "os.system",
    }:
        raise RuntimeError("Offline test blocked network or subprocess access")


def load_helper(path):
    spec = importlib.util.spec_from_file_location("cn_model_entry", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def child():
    # Fresh process and isolated HERMES_HOME for every provider.
    name = sys.argv[2]
    expected = json.loads(Path(sys.argv[3]).read_text())
    sys.addaudithook(deny_network)

    import hermes_cli.runtime_provider as runtime
    from hermes_cli.config import load_config

    config = load_config()
    model_config = config["model"]
    assert model_config["provider"] == f"custom:{name}", "config_provider"
    assert model_config["default"] == expected["model"], "config_model"
    assert model_config["base_url"].rstrip("/") == expected["base_url"], "config_url"

    resolved = runtime.resolve_runtime_provider(
        requested=f"custom:{name}",
        target_model=expected["model"],
    )
    assert resolved["base_url"].rstrip("/") == expected["base_url"], "runtime_url"
    assert resolved["api_key"] == expected["api_key"], "runtime_key"
    assert resolved["api_mode"] == "chat_completions", "runtime_protocol"

    resolved_model = resolved.get("model")
    if resolved_model:
        assert resolved_model == expected["model"], "runtime_model"

    print("ROUTING_TEST_PASS")


def parent():
    helper_path = Path(sys.argv[1]).resolve()
    install_root = Path(sys.argv[2]).resolve()
    helper = load_helper(helper_path)
    test_file = Path(__file__).resolve()

    # Blank preset fields use non-routable placeholders only in this offline test.
    placeholder_url = "https://offline-test.invalid/v1"
    placeholder_model = "offline-test-model"
    failures = []

    with tempfile.TemporaryDirectory(prefix="hermes-cn-routing-") as directory:
        root = Path(directory)
        store = root / "state/models"
        store.mkdir(parents=True, mode=0o700)

        for name, (_, base_url, model) in helper.PRESETS.items():
            base_url = base_url or placeholder_url
            model = model or placeholder_model
            key = f"OFFLINE_FAKE_KEY_{name.replace('-', '_')}"

            home = store / name
            home.mkdir(mode=0o700)
            config = helper.make_config(name, base_url, model, key)
            helper.write_new(
                home / "config.yaml",
                json.dumps(config, ensure_ascii=False) + "\n",
            )
            expected_path = root / f"{name}.expected.json"
            helper.write_new(
                expected_path,
                json.dumps({
                    "base_url": base_url.rstrip("/"),
                    "model": model,
                    "api_key": key,
                }) + "\n",
            )

            # Exercise the same environment builder used by product check/chat.
            env = helper.child_env(install_root, home)
            env["HOME"] = str(root)
            env["XDG_CONFIG_HOME"] = str(root / "xdg-config")
            env["XDG_CACHE_HOME"] = str(root / "xdg-cache")
            env["PYTHONDONTWRITEBYTECODE"] = "1"

            for variable in (
                "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
                "http_proxy", "https_proxy", "all_proxy", "no_proxy",
            ):
                env.pop(variable, None)

            command = [
                sys.executable, "-I", str(test_file),
                "--child", name, str(expected_path),
            ]
            try:
                result = subprocess.run(
                    command, env=env, cwd=root,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, errors="replace", timeout=45,
                )
                passed = (
                    result.returncode == 0
                    and "ROUTING_TEST_PASS" in result.stdout.splitlines()
                )
                print(f"{'PASS' if passed else 'FAIL'}：{name}", flush=True)
                if not passed:
                    failures.append(name)
                    # All provider credentials in this child are synthetic.
                    # Still redact them and do not echo full configuration.
                    lines = result.stdout.replace(key, "[FAKE_KEY]").splitlines()
                    for line in lines[-12:]:
                        print("  " + line)
            except subprocess.TimeoutExpired:
                failures.append(name)
                print(f"FAIL：{name}，离线路由解析超过 45 秒", flush=True)

        helper.activate(store, "deepseek")
        assert helper.selected(store) == "deepseek"
        helper.activate(store, "kimi")
        assert helper.selected(store) == "kimi"

        deepseek = helper.load_profile(store, "deepseek")[1]
        kimi = helper.load_profile(store, "kimi")[1]
        assert deepseek["api_key"] != kimi["api_key"]
        assert deepseek["base_url"] != kimi["base_url"]

        print("PASS：切换后各配置密钥与接口保持独立", flush=True)

    if failures:
        print("FAIL：尚未通过的路由：" + ", ".join(failures))
        return 1

    print(f"PASS：全部 {len(helper.PRESETS)} 个预设的固定 Hermes 路由解析")
    print("范围：真实运行时解析、假密钥、禁止联网；不代表真实模型对话通过。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--child":
        child()
    else:
        sys.exit(parent())
