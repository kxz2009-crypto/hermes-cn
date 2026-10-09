"""preflight 离线单元测试。

运行：python3 -m unittest test_preflight.py -v
不访问网络；通过构造 Report / monkeypatch 验证判定逻辑。
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import preflight  # noqa: E402
from preflight import (  # noqa: E402
    BLOCK, PASS, UNKNOWN, WARN, Check, Report,
)


class ReportLogicTest(unittest.TestCase):
    def test_overall_block_wins(self):
        r = Report(checks=[Check("a", PASS), Check("b", BLOCK),
                           Check("c", WARN)])
        self.assertEqual(r.overall(), BLOCK)

    def test_overall_warn(self):
        r = Report(checks=[Check("a", PASS), Check("b", WARN)])
        self.assertEqual(r.overall(), WARN)

    def test_overall_pass(self):
        r = Report(checks=[Check("a", PASS), Check("b", PASS)])
        self.assertEqual(r.overall(), PASS)

    def test_overall_unknown_hard(self):
        r = Report(checks=[Check("a", PASS), Check("b", UNKNOWN, hard=True)])
        self.assertEqual(r.overall(), UNKNOWN)

    def test_overall_unknown_soft_is_warn_or_pass(self):
        # 非必需项 UNKNOWN 不阻断总体
        r = Report(checks=[Check("a", PASS), Check("b", UNKNOWN, hard=False)])
        self.assertIn(r.overall(), (PASS, WARN))

    def test_json_roundtrip(self):
        import json
        r = Report(os_name="t", arch="x",
                   checks=[Check("a", PASS, "d", True)])
        d = json.loads(r.to_json())
        self.assertEqual(d["overall"], PASS)
        self.assertEqual(d["checks"][0]["status"], PASS)

    def test_human_contains_verdict(self):
        r = Report(checks=[Check("a", BLOCK, "bad")])
        text = r.human()
        self.assertIn("不通过", text)
        self.assertIn("不满足安装条件", text)


class OsArchTest(unittest.TestCase):
    def _rep(self):
        return Report()

    def test_windows_native_blocks(self):
        rep = self._rep()
        with mock.patch.object(preflight.platform, "system",
                               return_value="Windows"):
            preflight.check_os_and_arch(rep)
        self.assertEqual(rep.checks[0].status, BLOCK)

    def test_darwin_old_blocks(self):
        rep = self._rep()
        with mock.patch.object(preflight.platform, "system",
                               return_value="Darwin"), \
             mock.patch.object(preflight.platform, "machine",
                               return_value="arm64"), \
             mock.patch.object(preflight.platform, "mac_ver",
                               return_value=("14.1", "", "")):
            preflight.check_os_and_arch(rep)
        os_check = rep.checks[0]
        self.assertEqual(os_check.status, BLOCK)

    def test_darwin_15_arm_pass(self):
        rep = self._rep()
        with mock.patch.object(preflight.platform, "system",
                               return_value="Darwin"), \
             mock.patch.object(preflight.platform, "machine",
                               return_value="arm64"), \
             mock.patch.object(preflight.platform, "mac_ver",
                               return_value=("15.0", "", "")), \
             mock.patch.object(preflight, "_run", return_value=None):
            preflight.check_os_and_arch(rep)
        self.assertEqual(rep.checks[0].status, PASS)

    def test_linux_ubuntu2404_pass(self):
        rep = self._rep()
        os_release = 'PRETTY_NAME="Ubuntu 24.04.1 LTS"\nVERSION_ID="24.04"\n'
        with mock.patch.object(preflight.platform, "system",
                               return_value="Linux"), \
             mock.patch.object(preflight.platform, "machine",
                               return_value="x86_64"), \
             mock.patch.object(preflight, "_run",
                               side_effect=lambda cmd, **kw:
                                   os_release if "/etc/os-release" in cmd
                                   else "6.6-generic"):
            preflight.check_os_and_arch(rep)
        self.assertEqual(rep.checks[0].status, PASS)

    def test_linux_other_distro_warn(self):
        rep = self._rep()
        os_release = 'PRETTY_NAME="Debian GNU/Linux 12"\nVERSION_ID="12"\n'
        with mock.patch.object(preflight.platform, "system",
                               return_value="Linux"), \
             mock.patch.object(preflight.platform, "machine",
                               return_value="x86_64"), \
             mock.patch.object(preflight, "_run",
                               side_effect=lambda cmd, **kw:
                                   os_release if "/etc/os-release" in cmd
                                   else "6.1-generic"):
            preflight.check_os_and_arch(rep)
        self.assertEqual(rep.checks[0].status, WARN)
        self.assertFalse(rep.checks[0].hard)


class ResourceTest(unittest.TestCase):
    def test_low_memory_blocks(self):
        rep = Report()
        meminfo = "MemTotal:        4000000 kB\n"  # ~3.7 GB
        fake_open = mock.mock_open(read_data=meminfo)
        with mock.patch("builtins.open", fake_open):
            preflight.check_resources(rep)
        mem = [c for c in rep.checks if "内存" in c.name][0]
        self.assertEqual(mem.status, BLOCK)

    def test_mid_memory_warns(self):
        rep = Report()
        meminfo = "MemTotal:       10000000 kB\n"  # ~9.5 GB
        fake_open = mock.mock_open(read_data=meminfo)
        stat = mock.Mock(f_bavail=100 * 1024 ** 3 // 4096, f_frsize=4096)
        with mock.patch("builtins.open", fake_open), \
             mock.patch.object(preflight.os, "statvfs", return_value=stat):
            preflight.check_resources(rep)
        mem = [c for c in rep.checks if "内存" in c.name][0]
        self.assertEqual(mem.status, WARN)

    def test_low_disk_blocks(self):
        rep = Report()
        meminfo = "MemTotal:       32000000 kB\n"
        stat = mock.Mock(f_bavail=10 * 1024 ** 3 // 4096, f_frsize=4096)
        fake_open = mock.mock_open(read_data=meminfo)
        with mock.patch("builtins.open", fake_open), \
             mock.patch.object(preflight.os, "statvfs", return_value=stat):
            preflight.check_resources(rep)
        disk = [c for c in rep.checks if "磁盘" in c.name][0]
        self.assertEqual(disk.status, BLOCK)


class ToolsTest(unittest.TestCase):
    def test_python_version_gate_expression(self):
        # 判定表达式直接验证：3.9 < 3.11 → False；3.11+ → True
        # （sys.version_info 是 namedtuple，与 (3,11) 比较安全）
        from collections import namedtuple
        VI = namedtuple("version_info", "major minor micro releaselevel serial")
        self.assertFalse(VI(3, 9, 0, "final", 0) >= (3, 11))
        self.assertTrue(VI(3, 11, 0, "final", 0) >= (3, 11))
        self.assertTrue(VI(3, 14, 7, "final", 0) >= (3, 11))


class RunAllTest(unittest.TestCase):
    def test_exception_becomes_unknown(self):
        with mock.patch.object(preflight, "check_os_and_arch",
                               side_effect=RuntimeError("boom")):
            rep = preflight.run_all()
        statuses = {c.name: c.status for c in rep.checks}
        self.assertEqual(statuses.get("系统与架构"), UNKNOWN)
        # 其他检测项仍执行（步骤标签为单项名，验证后续项出现）
        self.assertIn("内存容量", statuses)
        self.assertIn("主目录写权限", statuses)


if __name__ == "__main__":
    unittest.main(verbosity=2)
