"""Quota / GuardedAssistant 离线单元测试（不联网、不写生产库）。

运行：python3 -m unittest test_quota.py -v
依赖：仅 Python 标准库。quota.py / guarded_app.py / assistant_app.py
须与本文件同目录（候选副本）。
"""
import calendar
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quota import Quota, QuotaExceeded  # noqa: E402


class FakeClock:
    def __init__(self, t):
        self.t = t

    def __call__(self):
        return self.t


class QuotaTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.remove(self.path)  # Quota 要求路径不存在且父目录存在
        self.base = calendar.timegm((2026, 10, 9, 2, 0, 0, 0, 0, 0))
        self.clock = FakeClock(self.base)  # 北京 10:00

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def test_per_minute_limit(self):
        q = Quota(self.path, "s" * 32, clock=self.clock)
        for i in range(3):
            q.release(q.reserve("198.51.100.1"))
        with self.assertRaises(QuotaExceeded):
            q.reserve("198.51.100.1")  # 第4次同分钟被拒

    def test_minute_window_resets(self):
        q = Quota(self.path, "s" * 32, clock=self.clock)
        for i in range(3):
            q.release(q.reserve("198.51.100.1"))
        with self.assertRaises(QuotaExceeded):
            q.reserve("198.51.100.1")
        self.clock.t += 61  # 下一分钟
        q.release(q.reserve("198.51.100.1"))  # 重新可用

    def test_per_day_limit(self):
        q = Quota(self.path, "s" * 32, clock=self.clock)
        ok = 0
        try:
            for i in range(25):
                self.clock.t = self.base + i * 61  # 跨分钟避免分钟桶
                q.release(q.reserve("198.51.100.1"))
                ok += 1
        except QuotaExceeded:
            pass
        self.assertEqual(ok, 20)  # 第21次被拒

    def test_beijing_day_rollover(self):
        day_end = calendar.timegm((2026, 10, 9, 15, 59, 55, 0, 0, 0))
        self.clock.t = day_end  # 北京 23:59:55
        q = Quota(self.path, "s" * 32, clock=self.clock)
        for i in range(3):
            q.release(q.reserve("198.51.100.2"))
        self.clock.t = day_end + 10  # 北京次日 00:00:05
        q.release(q.reserve("198.51.100.2"))  # 跨北京时间日后重新可用

    def test_global_day_limit(self):
        q = Quota(self.path, "s" * 32, global_day=3, clock=self.clock)
        addrs = ["203.0.113.1", "203.0.113.2", "203.0.113.3", "203.0.113.4"]
        ok = 0
        try:
            for a in addrs * 2:
                q.release(q.reserve(a))
                ok += 1
        except QuotaExceeded:
            pass
        self.assertEqual(ok, 3)  # 第4次触发全站日限

    def test_concurrent_leases(self):
        q = Quota(self.path, "s" * 32, clock=self.clock)
        t1 = q.reserve("198.51.100.3")
        t2 = q.reserve("198.51.100.4")
        with self.assertRaises(QuotaExceeded):
            q.reserve("198.51.100.5")  # 第3个并发被拒
        q.release(t1)
        t3 = q.reserve("198.51.100.5")  # 释放后可进入
        q.release(t2)
        q.release(t3)

    def test_identity_not_reversible(self):
        # 同地址不同日 → 不同 HMAC；同日同地址 → 相同；库中无明文地址
        import sqlite3
        q = Quota(self.path, "s" * 32, clock=self.clock)
        q.release(q.reserve("198.51.100.6"))
        db = sqlite3.connect(self.path)
        rows = db.execute("SELECT bucket FROM counters").fetchall()
        db.close()
        joined = " ".join(r[0] for r in rows)
        self.assertNotIn("198.51.100.6", joined)

    def test_persistence_across_restart(self):
        # 重启（新实例同库同密钥）不清零
        q = Quota(self.path, "s" * 32, clock=self.clock)
        for i in range(3):
            q.release(q.reserve("198.51.100.7"))
        with self.assertRaises(QuotaExceeded):
            q.reserve("198.51.100.7")
        q2 = Quota(self.path, "s" * 32, clock=self.clock)  # 模拟重启
        with self.assertRaises(QuotaExceeded):
            q2.reserve("198.51.100.7")

    def test_secret_too_short(self):
        with self.assertRaises(ValueError):
            Quota(self.path, "short")

    def test_db_path_symlink_rejected(self):
        link = self.path + ".link"
        os.symlink("/etc/passwd", link)
        try:
            with self.assertRaises(ValueError):
                Quota(link, "s" * 32)
        finally:
            os.remove(link)

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):
            Quota(self.path, "s" * 32, per_minute=0)


class GuardedAssistantTest(unittest.TestCase):
    """guarded_app 层：只测 dispatch 的门控行为，不请求模型。"""

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        os.remove(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.remove(self.path)

    def _app(self):
        # 构造最小知识库目录（hash/size 由实际文件算出），
        # 门控测试不触达模型调用（endpoint 为空时 answer 先于 quota 检查前
        # 只在 dispatch 之后发生；本测试只验证 dispatch 门控）。
        import hashlib
        import json
        kb = tempfile.mkdtemp()
        self.addCleanup(lambda: __import__("shutil").rmtree(kb, True))
        for name in ("PRODUCT_RULES.md", "INSTALL_GUIDE.md"):
            data = f"test knowledge {name}\n".encode()
            with open(os.path.join(kb, name), "wb") as fh:
                fh.write(data)
        manifest = {"files": {}}
        for name in ("PRODUCT_RULES.md", "INSTALL_GUIDE.md"):
            with open(os.path.join(kb, name), "rb") as fh:
                data = fh.read()
            manifest["files"][name] = {
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        with open(os.path.join(kb, "manifest.json"), "w") as fh:
            json.dump(manifest, fh)
        from guarded_app import GuardedAssistant
        quota = Quota(self.path, "s" * 32)
        return GuardedAssistant(
            knowledge=kb, quota=quota,
            endpoint="", key="", model="",
        )

    def test_rejects_non_loopback_remote(self):
        app = self._app()
        environ = {
            "PATH_INFO": "/api/install-assistant/chat",
            "REQUEST_METHOD": "POST",
            "REMOTE_ADDR": "10.0.0.5",
        }
        with self.assertRaises(Exception) as ctx:
            app.dispatch(environ)
        self.assertEqual(getattr(ctx.exception, "status", None), 403)

    def test_rejects_missing_or_bad_x_real_ip(self):
        app = self._app()
        for header in ("", "not-an-ip", "999.1.1.1"):
            environ = {
                "PATH_INFO": "/api/install-assistant/chat",
                "REQUEST_METHOD": "POST",
                "REMOTE_ADDR": "127.0.0.1",
                "HTTP_X_REAL_IP": header,
            }
            with self.assertRaises(Exception) as ctx:
                app.dispatch(environ)
            self.assertEqual(getattr(ctx.exception, "status", None), 403)

    def test_healthz_bypasses_quota(self):
        app = self._app()
        environ = {
            "PATH_INFO": "/healthz",
            "REQUEST_METHOD": "GET",
            "REMOTE_ADDR": "127.0.0.1",
        }
        status, _ = app.dispatch(environ)
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
