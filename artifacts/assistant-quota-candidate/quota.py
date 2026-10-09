import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path

class QuotaExceeded(Exception):
    pass

class Quota:
    def __init__(self, path, secret, per_minute=3, per_day=20,
                 global_day=100, concurrent=2, clock=time.time):
        self.path = str(path)
        self.secret = secret.encode()
        self.clock = clock
        self.per_minute = per_minute
        self.per_day = per_day
        self.global_day = global_day
        self.concurrent = concurrent
        if len(self.secret) < 32:
            raise ValueError("Quota secret is too short")
        if not Path(path).parent.is_dir() or Path(path).is_symlink():
            raise ValueError("Invalid quota database path")
        if min(per_minute, per_day, global_day, concurrent) < 1:
            raise ValueError("Invalid quota limits")
        db = self.connect()
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS counters (
                    bucket TEXT PRIMARY KEY,
                    count INTEGER NOT NULL,
                    expires INTEGER NOT NULL
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS leases (
                    token TEXT PRIMARY KEY,
                    expires INTEGER NOT NULL
                )
            """)
        finally:
            db.close()

    def connect(self):
        return sqlite3.connect(
            self.path, timeout=5, isolation_level=None
        )

    def reserve(self, address):
        now = int(self.clock())
        day = (now + 28800) // 86400
        day_end = (day + 1) * 86400 - 28800
        minute = now // 60
        identity = hmac.new(
            self.secret, f"{day}|{address}".encode(),
            hashlib.sha256,
        ).hexdigest()
        buckets = [
            (f"global:{day}", self.global_day, day_end),
            (f"ip-day:{day}:{identity}", self.per_day, day_end),
            (f"ip-minute:{minute}:{identity}",
             self.per_minute, (minute + 1) * 60),
        ]
        token = secrets.token_hex(16)
        db = self.connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM leases WHERE expires <= ?", (now,))
            db.execute("DELETE FROM counters WHERE expires <= ?", (now,))
            active = db.execute("SELECT COUNT(*) FROM leases").fetchone()[0]
            if active >= self.concurrent:
                raise QuotaExceeded("同时提问较多，请稍后再试。")

            for bucket, limit, expires in buckets:
                row = db.execute(
                    "SELECT count FROM counters WHERE bucket = ?", (bucket,)
                ).fetchone()
                if row and row[0] >= limit:
                    raise QuotaExceeded(
                        "已达到本时段提问次数限制，请稍后再试或查看安装指南。"
                    )
            for bucket, limit, expires in buckets:
                db.execute("""
                    INSERT INTO counters(bucket, count, expires)
                    VALUES (?, 1, ?)
                    ON CONFLICT(bucket) DO UPDATE SET count = count + 1
                """, (bucket, expires))
            # 需配合小于此时长的服务进程请求超时。
            db.execute(
                "INSERT INTO leases(token, expires) VALUES (?, ?)",
                (token, now + 90),
            )
            db.commit()
            return token
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def release(self, token):
        db = self.connect()
        try:
            db.execute("DELETE FROM leases WHERE token = ?", (token,))
        finally:
            db.close()
