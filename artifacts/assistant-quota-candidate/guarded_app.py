from contextvars import ContextVar
import ipaddress
import os

from assistant_app import Assistant, Failure
from quota import Quota, QuotaExceeded

request_address = ContextVar("request_address", default=None)

class GuardedAssistant(Assistant):
    def __init__(self, *args, quota, **kwargs):
        super().__init__(*args, **kwargs)
        self.quota = quota

    def dispatch(self, environ):
        if environ.get("PATH_INFO") != "/api/install-assistant/chat":
            return super().dispatch(environ)
        # 正式部署只监听本机，由 Nginx 覆盖设置 X-Real-IP。
        # 不接受来自公网连接自行声明的转发地址。
        if environ.get("REMOTE_ADDR") != "127.0.0.1":
            raise Failure(403, "请通过本站入口提问。")
        try:
            address = str(ipaddress.ip_address(
                environ.get("HTTP_X_REAL_IP", "")
            ))
        except ValueError:
            raise Failure(403, "请求来源无法确认。") from None
        context = request_address.set(address)
        try:
            return super().dispatch(environ)
        finally:
            request_address.reset(context)

    def answer(self, messages):
        if not self.endpoint or not self.key or not self.model:
            raise Failure(503, "AI 问答尚未启用，请先查看安装指南。")
        address = request_address.get()
        if address is None:
            raise Failure(403, "请求来源无法确认。")
        try:
            token = self.quota.reserve(address)
        except QuotaExceeded as error:
            raise Failure(429, str(error)) from None
        try:
            # 尝试调用后即计一次，失败也不退回次数，避免反复重试。
            return super().answer(messages)
        finally:
            self.quota.release(token)

def create_app():
    quota = Quota(
        os.environ["ASSISTANT_QUOTA_DB"],
        os.environ["ASSISTANT_QUOTA_SECRET"],
    )
    return GuardedAssistant(
        knowledge=os.environ["ASSISTANT_KNOWLEDGE_DIR"],
        endpoint=os.environ.get("ASSISTANT_API_URL", ""),
        key=os.environ.get("ASSISTANT_API_KEY", ""),
        model=os.environ.get("ASSISTANT_MODEL", ""),
        quota=quota,
    )
