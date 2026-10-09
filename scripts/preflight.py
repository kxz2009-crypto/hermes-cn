"""preflight — Hermes-CN 安装前环境检测器（Phase 2 阶段 B）。

设计约束：
- 仅用 Python 标准库；只读检测，不安装/升级/修改任何系统状态。
- 输出双格式：机器可读 JSON + 用户可读中文报告。
- 结果四态：PASS / WARN / BLOCK / UNKNOWN；UNKNOWN 不视为通过。
- 硬性技术要求（BLOCK 级）与推荐配置（WARN 级）分开判定。

用法：
    python3 preflight.py            # 人类报告 + 末尾 JSON
    python3 preflight.py --json     # 仅 JSON（stdout）
    python3 preflight.py --summary  # 仅人类报告

任何检测项抛异常 → 该项 UNKNOWN，不阻断其他项。
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import socket
import ssl
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

PASS, WARN, BLOCK, UNKNOWN = "PASS", "WARN", "BLOCK", "UNKNOWN"

# 硬性最低要求（BLOCK 级）——与安装指南一致
MIN_DISK_GB = 20.0
MIN_MEM_GB = 8.0          # 硬性下限；指南推荐 16 GB
REC_MEM_GB = 16.0         # 推荐值，低于则 WARN
REC_DISK_GB = 40.0        # 推荐值

PROBE_URLS = [
    ("官方源 GitHub", "https://github.com"),
    ("PyPI 清华镜像", "https://pypi.tuna.tsinghua.edu.cn/simple/"),
    ("本站下载服务", "https://hermes.localvram.cn/robots.txt"),
]
PROBE_TIMEOUT = 8


@dataclass
class Check:
    name: str
    status: str
    detail: str = ""
    hard: bool = True   # True=硬性要求(False=推荐/信息项)


@dataclass
class Report:
    os_name: str = ""
    arch: str = ""
    checks: list = field(default_factory=list)

    def to_json(self) -> str:
        d = asdict(self)
        d["overall"] = self.overall()
        return json.dumps(d, ensure_ascii=False, indent=2)

    def overall(self) -> str:
        statuses = {c.status for c in self.checks}
        if BLOCK in statuses:
            return BLOCK
        if UNKNOWN in statuses and any(c.hard for c in self.checks
                                       if c.status == UNKNOWN):
            return UNKNOWN
        if WARN in statuses:
            return WARN
        return PASS

    def human(self) -> str:
        icon = {PASS: "通过", WARN: "警告", BLOCK: "不通过",
                UNKNOWN: "无法确认"}
        lines = [
            "===== Hermes 安装环境检查 =====",
            f"系统：{self.os_name} | 架构：{self.arch}",
            "",
        ]
        for c in self.checks:
            tag = f"[{icon.get(c.status, c.status)}]"
            kind = "必需" if c.hard else "建议"
            lines.append(f"{tag}({kind}) {c.name}")
            if c.detail:
                lines.append(f"      {c.detail}")
        lines.append("")
        overall = self.overall()
        verdict = {
            PASS: "环境满足安装条件。",
            WARN: "可以安装，但警告项可能影响体验。",
            BLOCK: "当前环境不满足安装条件，请先处理“不通过”项。",
            UNKNOWN: "部分项目无法确认，请补充信息后重试；"
                     "无法确认的必需项不视为通过。",
        }[overall]
        lines.append(f"总体结论：{icon[overall]} — {verdict}")
        return "\n".join(lines)


def _run(cmd: list, timeout: int = 10) -> Optional[str]:
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
            env={**os.environ, "LC_ALL": "C"},
        )
        if r.returncode == 0:
            return r.stdout.strip()
        return None
    except (OSError, subprocess.TimeoutExpired):
        return None


def check_os_and_arch(rep: Report) -> None:
    system = platform.system()
    machine = platform.machine()
    rep.arch = machine
    if system == "Linux":
        release = _run(["cat", "/etc/os-release"])
        name = "Linux"
        if release:
            m = re.search(r'PRETTY_NAME="([^"]+)"', release)
            if m:
                name = m.group(1)
        rep.os_name = name
        if "Ubuntu" not in name:
            rep.checks.append(Check(
                "操作系统", WARN, f"检测到 {name}；"
                "当前验证范围为 Ubuntu 24.04，其他发行版未验证。",
                hard=False))
        else:
            ver = re.search(r'VERSION_ID="?([0-9.]+)', release or "")
            if ver and ver.group(1).startswith("24.04"):
                rep.checks.append(Check(
                    "操作系统", PASS, f"{name}（已验证平台）"))
            else:
                rep.checks.append(Check(
                    "操作系统", WARN, f"{name}；已验证平台为 Ubuntu 24.04。",
                    hard=False))
        # WSL 检测
        wsl = _run(["uname", "-r"]) or ""
        if "microsoft" in wsl.lower():
            rep.checks.append(Check(
                "WSL 环境", PASS, f"WSL2 内核 {wsl}"))
    elif system == "Darwin":
        ver = platform.mac_ver()[0]
        rep.os_name = f"macOS {ver}"
        major = int(ver.split(".")[0]) if ver else 0
        if major >= 15:
            rep.checks.append(Check("操作系统", PASS, rep.os_name))
        else:
            rep.checks.append(Check(
                "操作系统", BLOCK,
                f"{rep.os_name}；当前要求 macOS 15 及以上。"))
        if machine == "arm64":
            rosetta = _run(["/usr/bin/pgrep", "-q", "-x", "oahd"])
            # pgrep -q 在 macOS 不可用，退回普通方式
            if rosetta is None:
                rosetta = _run(["/usr/sbin/sysctl", "-n",
                                "sysctl.proc_translated"])
            translated = (rosetta == "1")
            rep.checks.append(Check(
                "CPU 架构", PASS if not translated else WARN,
                "Apple Silicon" + ("（Rosetta 转译运行）" if translated
                                   else "（原生 ARM64）")))
    elif system == "Windows":
        rep.os_name = f"Windows {platform.release()}"
        rep.checks.append(Check(
            "操作系统", BLOCK,
            "不支持 Windows 原生运行本检测流程；请在 WSL (Ubuntu) 内运行。"))
    else:
        rep.os_name = system
        rep.checks.append(Check(
            "操作系统", BLOCK, f"未验证的平台：{system}"))


def check_resources(rep: Report) -> None:
    # 内存
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal"):
                    mem_kb = int(line.split()[1])
                    break
            else:
                mem_kb = None
    except OSError:
        mem_kb = None
    if mem_kb is None and sys.platform == "darwin":
        out = _run(["/usr/sbin/sysctl", "-n", "hw.memsize"])
        mem_kb = int(out) // 1024 if out else None
    if mem_kb is None:
        rep.checks.append(Check(
            "内存容量", UNKNOWN, "无法读取内存信息。"))
    else:
        mem_gb = mem_kb / 1024 / 1024
        if mem_gb < MIN_MEM_GB:
            rep.checks.append(Check(
                "内存容量", BLOCK,
                f"{mem_gb:.1f} GB，低于最低要求 {MIN_MEM_GB} GB。"))
        elif mem_gb < REC_MEM_GB:
            rep.checks.append(Check(
                "内存容量", WARN,
                f"{mem_gb:.1f} GB；可用即可，推荐 {REC_MEM_GB} GB 以上。",
                hard=False))
        else:
            rep.checks.append(Check(
                "内存容量", PASS, f"{mem_gb:.1f} GB"))

    # 磁盘（当前目录所在盘）
    try:
        st = os.statvfs(os.path.expanduser("~"))
        free_gb = st.f_bavail * st.f_frsize / 1024 ** 3
    except OSError:
        free_gb = None
    if free_gb is None:
        rep.checks.append(Check(
            "磁盘空间", UNKNOWN, "无法读取磁盘容量。"))
    else:
        if free_gb < MIN_DISK_GB:
            rep.checks.append(Check(
                "磁盘空间", BLOCK,
                f"可用 {free_gb:.1f} GB，低于最低要求 {MIN_DISK_GB} GB。"))
        elif free_gb < REC_DISK_GB:
            rep.checks.append(Check(
                "磁盘空间", WARN,
                f"可用 {free_gb:.1f} GB；推荐预留 {REC_DISK_GB} GB。",
                hard=False))
        else:
            rep.checks.append(Check(
                "磁盘空间", PASS, f"可用 {free_gb:.1f} GB"))


def check_tools(rep: Report) -> None:
    # Python
    ver = f"{sys.version_info.major}.{sys.version_info.minor}."           f"{sys.version_info.micro}"
    if sys.version_info >= (3, 11):
        rep.checks.append(Check("Python", PASS, f"Python {ver}"))
    else:
        rep.checks.append(Check(
            "Python", BLOCK,
            f"Python {ver}；需要 3.11+（安装器使用 3.11.17）。"))

    for tool, minimum in (("python3", None), ("git", None),
                          ("curl", None)):
        path = shutil.which(tool)
        if path:
            rep.checks.append(Check(
                f"工具 {tool}", PASS, path))
        else:
            rep.checks.append(Check(
                f"工具 {tool}", BLOCK, "未找到，请先安装。"))

    # venv 可用性
    try:
        import venv  # noqa: F401
        rep.checks.append(Check("venv 模块", PASS, "可导入"))
    except ImportError:
        rep.checks.append(Check(
            "venv 模块", BLOCK,
            "Python venv 模块不可用（Ubuntu 需安装 python3-venv）。"))


def check_network(rep: Report) -> None:
    # DNS
    try:
        socket.getaddrinfo("pypi.tuna.tsinghua.edu.cn", 443)
        rep.checks.append(Check("DNS 解析", PASS, "清华镜像域名解析正常"))
    except OSError as e:
        rep.checks.append(Check("DNS 解析", BLOCK, f"解析失败：{e}"))
        rep.checks.append(Check(
            "下载源可达性", UNKNOWN, "DNS 未通，跳过探测。"))
        return

    ctx = ssl.create_default_context()
    for label, url in PROBE_URLS:
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "hermes-preflight/1"})
            with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT,
                                        context=ctx) as resp:
                rep.checks.append(Check(
                    f"下载源 {label}", PASS, f"HTTPS {resp.status}"))
        except Exception as e:
            # 网络探测失败默认 WARN（可重试），本站源 BLOCK 会阻断交付
            hard = "本站" in label
            rep.checks.append(Check(
                f"下载源 {label}", BLOCK if hard else WARN,
                f"不可达：{type(e).__name__}；可稍后重试。", hard=hard))


def check_existing_install(rep: Report) -> None:
    home = os.path.expanduser("~")
    candidates = [
        ("本项目目录", os.path.join(home, "hermes-work")),
        ("用户已有 Hermes", os.path.join(home, ".hermes")),
    ]
    for label, path in candidates:
        if not os.path.exists(path):
            rep.checks.append(Check(
                f"目录占用 {label}", PASS, f"{path} 不存在，可全新安装"))
        elif os.path.islink(path):
            rep.checks.append(Check(
                f"目录占用 {label}", WARN,
                f"{path} 是符号链接；安装前需人工确认。",
                hard=False))
        elif os.path.isdir(path):
            rep.checks.append(Check(
                f"目录占用 {label}", WARN,
                f"{path} 已存在；安装器将保留既有内容，不会覆盖配置。",
                hard=False))
        else:
            rep.checks.append(Check(
                f"目录占用 {label}", BLOCK,
                f"{path} 是普通文件，路径被占用。"))

    # 写权限
    test_dir = os.path.join(home, ".hermes-preflight-probe")
    try:
        os.makedirs(test_dir, exist_ok=True)
        probe = os.path.join(test_dir, ".w")
        with open(probe, "w") as fh:
            fh.write("1")
        os.remove(probe)
        os.rmdir(test_dir)
        rep.checks.append(Check(
            "主目录写权限", PASS, "可创建目录与文件"))
    except OSError as e:
        rep.checks.append(Check(
            "主目录写权限", BLOCK, f"写入失败：{e}"))


def run_all() -> Report:
    rep = Report()
    steps: list[tuple[str, Callable]] = [
        ("系统与架构", check_os_and_arch),
        ("资源容量", check_resources),
        ("工具链", check_tools),
        ("网络与下载源", check_network),
        ("既有安装与权限", check_existing_install),
    ]
    for label, fn in steps:
        try:
            fn(rep)
        except Exception as e:  # 单项异常不拖垮整体
            rep.checks.append(Check(
                f"{label}", UNKNOWN,
                f"检测过程异常：{type(e).__name__}"))
    return rep


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Hermes 安装环境检测")
    parser.add_argument("--json", action="store_true", help="仅输出 JSON")
    parser.add_argument("--summary", action="store_true",
                        help="仅输出人类报告")
    parser.add_argument("--offline", action="store_true",
                        help="跳过网络探测（下载源可达性标记 UNKNOWN）")
    args = parser.parse_args(argv)

    if args.offline:
        global PROBE_URLS
        PROBE_URLS = []

    rep = run_all()
    if args.json:
        print(rep.to_json())
    elif args.summary:
        print(rep.human())
    else:
        print(rep.human())
        print()
        print("===== JSON =====")
        print(rep.to_json())
    return 0 if rep.overall() in (PASS, WARN) else 1


if __name__ == "__main__":
    sys.exit(main())
