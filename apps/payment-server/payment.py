"""Hermes CN virtual-payment service. Standard library, independent SQLite storage."""
import hashlib, hmac, json, os, re, secrets, sqlite3, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import urlencode, urlparse, parse_qs
from xml.etree import ElementTree
from aes_callbacks import decrypt_callback, CallbackCryptoError

APP_ID = "wx9e5937d752f2125f"
PRODUCT = {"id": "hermes_install_990", "name": "Hermes CN 自助安装包",
           "priceFen": 990, "version": "3861473", "rulesVersion": "draft-v1", "claimDays": None}

class Failure(Exception):
    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code, self.status = code, status

def require(ok, code, message, status=400):
    if not ok: raise Failure(code, message, status)

def mac(key, value):
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()

def sha(value): return hashlib.sha256(value.encode()).hexdigest()
def uid(prefix): return prefix + secrets.token_hex(12)

class Wechat:
    def __init__(self, config=None, transport=None):
        self.c = config if config is not None else os.environ
        self.transport = transport or self.http
        self.token, self.token_until = "", 0

    def ready(self):
        keys = ("HERMES_APP_SECRET", "HERMES_VP_APP_KEY")
        require(self.c.get("HERMES_PAYMENT_ENABLED") == "1" and all(self.c.get(k) for k in keys),
                "PAYMENT_NOT_CONFIGURED", "支付服务尚未配置完成，暂不能付款。", 503)
        require(self.c.get("HERMES_APP_ID", APP_ID) == APP_ID, "APPID_MISMATCH", "支付应用配置不一致。", 503)
        require(self.c.get("HERMES_VP_ENV", "0") in ("0", "1"), "ENV_INVALID", "支付环境配置无效。", 503)

    @staticmethod
    def http(url, body=None):
        try:
            data = None if body is None else body.encode()
            req = Request(url, data=data, headers={"Content-Type": "application/json"})
            with urlopen(req, timeout=12) as res: return json.loads(res.read(1024 * 1024))
        except Exception:
            # Do not return URLs (which contain credentials), tokens, or upstream bodies.
            raise Failure("WECHAT_UNAVAILABLE", "微信服务暂时不可用，请稍后查询订单。", 502)

    def call(self, url, body=None):
        result = self.transport(url, body)
        require(isinstance(result, dict), "WECHAT_RESPONSE", "微信服务返回格式异常。", 502)
        require(not result.get("errcode"), "WECHAT_REJECTED", "微信接口暂未完成操作，请稍后重试。", 502)
        return result

    def login(self, code):
        self.ready()
        q = urlencode({"appid": APP_ID, "secret": self.c["HERMES_APP_SECRET"],
                       "js_code": code, "grant_type": "authorization_code"})
        data = self.call("https://api.weixin.qq.com/sns/jscode2session?" + q)
        require(data.get("openid") and data.get("session_key"), "LOGIN_FAILED", "微信登录失败，请重新打开小程序。", 401)
        return data["openid"], data["session_key"]

    def access_token(self):
        self.ready()
        if self.token_until > time.time(): return self.token
        body = json.dumps({"grant_type": "client_credential", "appid": APP_ID,
                           "secret": self.c["HERMES_APP_SECRET"]}, separators=(",", ":"))
        data = self.call("https://api.weixin.qq.com/cgi-bin/stable_token", body)
        require(data.get("access_token"), "TOKEN_FAILED", "微信服务凭证不可用。", 502)
        self.token = data["access_token"]
        self.token_until = time.time() + max(0, int(data.get("expires_in", 7200)) - 300)
        return self.token

    def xpay(self, path, data, session_key=None):
        self.ready()
        data = {**data, "env": int(self.c.get("HERMES_VP_ENV", "0"))}
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        query = {"access_token": self.access_token(), "pay_sig": mac(self.c["HERMES_VP_APP_KEY"], path + "&" + body)}
        if session_key: query["signature"] = mac(session_key, body)
        q = urlencode(query)
        return self.call("https://api.weixin.qq.com" + path + "?" + q, body)

    def params(self, order, session_key):
        self.ready()
        data = {"offerId": self.c.get("HERMES_VP_OFFER_ID", "1450674694"),
                "buyQuantity": 1, "env": int(self.c.get("HERMES_VP_ENV", "0")),
                "currencyType": "CNY", "productId": PRODUCT["id"],
                "goodsPrice": PRODUCT["priceFen"], "outTradeNo": order["id"],
                "attach": order["checkId"]}
        raw = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return {"mode": "short_series_goods", "signData": raw,
                "paySig": mac(self.c["HERMES_VP_APP_KEY"], "requestVirtualPayment&" + raw),
                "signature": mac(session_key, raw)}

    def query(self, order):
        data = self.xpay("/xpay/query_order", {"openid": order["openid"], "order_id": order["id"]})
        require(isinstance(data.get("order"), dict), "ORDER_QUERY_FAILED", "微信订单查询暂未返回结果。", 502)
        return data["order"]

    def query_refund(self, order, refund_id):
        data=self.xpay("/xpay/query_order",{"openid":order["openid"],"order_id":refund_id})
        require(isinstance(data.get("order"),dict),"REFUND_QUERY_FAILED","退款查询暂未返回结果。",502)
        return data["order"]

    def delivered(self, order):
        body=json.dumps({"order_id":order["id"],"env":int(self.c.get("HERMES_VP_ENV","0"))},separators=(",",":"))
        q=urlencode({"access_token":self.access_token()})
        return self.call("https://api.weixin.qq.com/xpay/notify_provide_goods?"+q,body)

    def refund(self, order, refund_id, left_fee, session_key):
        return self.xpay("/xpay/refund_order", {"openid": order["openid"], "order_id": order["id"],
            "refund_order_id": refund_id, "left_fee": left_fee, "refund_fee": PRODUCT["priceFen"],
            "refund_reason": "3", "req_from": "2", "biz_meta": order["id"]}, session_key)

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.RLock()
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("CREATE TABLE IF NOT EXISTS records(kind TEXT,key TEXT,body TEXT,PRIMARY KEY(kind,key))")
        self.db.commit()
        if path != ":memory:": os.chmod(path, 0o600)

    def get(self, kind, key):
        row = self.db.execute("SELECT body FROM records WHERE kind=? AND key=?", (kind, key)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, kind, key, value):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO records VALUES(?,?,?)",
                            (kind, key, json.dumps(value, ensure_ascii=False)))

    def all(self, kind):
        return [json.loads(x[0]) for x in self.db.execute("SELECT body FROM records WHERE kind=?", (kind,))]

class Service:
    def __init__(self, store, provider, clock=None):
        self.s, self.p, self.now = store, provider, clock or (lambda: int(time.time()*1000))
        self.sessions = {}
        self.last_queries = {}

    def login(self, code):
        require(isinstance(code, str) and 0 < len(code) <= 256, "LOGIN_CODE", "缺少微信登录码。")
        openid, key = self.p.login(code)
        token = secrets.token_urlsafe(32)
        # session_key stays in memory; never returned or placed in order/database/log.
        self.sessions[sha(token)] = {"openid": openid, "key": key, "until": self.now()+3600000}
        return {"token": token}

    def auth(self, token):
        s = self.sessions.get(sha(token))
        require(s and s["until"] > self.now(), "LOGIN_EXPIRED", "登录已过期，请重新登录。", 401)
        return s

    def provision_check(self, data):
        # Internal trusted checker/admin only. Never accept a client-created PASS for payment.
        require(data.get("status") == "PASS" and data.get("productVersion") == PRODUCT["version"],
                "CHECK_INVALID", "只有经过服务端核验的检查结果可以关联。")
        code, pc = secrets.token_urlsafe(18), secrets.token_urlsafe(32)
        c = {"id": uid("check"), "code": code, "status": "PASS", "confirmed": False,
             "productVersion": PRODUCT["version"], "environment": str(data.get("environment", ""))[:200],
             "expiresAt": self.now()+30*60000, "owner": None, "pcHash": sha(pc)}
        self.s.put("check", code, c)
        return {"code": code, "pcToken": pc, "expiresAt": c["expiresAt"]}

    @staticmethod
    def check_view(c): return {k:v for k,v in c.items() if k not in ("owner", "pcHash", "code")}

    def link(self, user, code):
        c = self.s.get("check", code)
        require(c and c["expiresAt"] > self.now(), "LINK_EXPIRED", "关联码无效或已过期，请回电脑重新检查。")
        require(c["owner"] in (None, user["openid"]), "LINK_USED", "这台电脑已关联其他微信账号。", 403)
        c["owner"] = user["openid"]; self.s.put("check", code, c)
        return self.check_view(c)

    def find_check(self, user, check_id):
        c = next((c for c in self.s.all("check") if c["id"] == check_id), None)
        require(c and c["owner"] == user["openid"], "CHECK_NOT_FOUND", "找不到已关联的电脑检查。", 403)
        require(c["expiresAt"] > self.now(), "CHECK_EXPIRED", "电脑检查已过期，请重新检查。")
        require(c["productVersion"] == PRODUCT["version"] and c["status"] == "PASS", "CHECK_CHANGED", "请重新检查电脑。")
        return c

    def confirm_check(self, user, check_id):
        c = self.find_check(user, check_id); c["confirmed"] = True
        self.s.put("check", c["code"], c); return self.check_view(c)

    def create_order(self, user, check_id, platform):
        c = self.find_check(user, check_id)
        require(c["confirmed"], "LINK_UNCONFIRMED", "请先确认关联的电脑。")
        old = next((o for o in self.s.all("order") if o["openid"]==user["openid"] and
                    o["checkId"]==check_id and o["paymentStatus"] in ("pending", "paid")), None)
        if old: return self.view(old)
        existing = [o for o in self.s.all("order") if o["openid"] == user["openid"] and o["product"]["version"] == PRODUCT["version"]]
        held = next((o for o in existing if o["paymentStatus"] == "paid" and o["refundStatus"] in ("requested","processing")), None)
        require(not held,"REFUND_IN_PROGRESS","原订单正在处理退款，请先查看原订单。")
        paid = next((o for o in existing if o["paymentStatus"] == "paid" and o["refundStatus"] in ("none","failed")), None)
        if paid:
            paid = self.reconcile(paid,True)
            if paid["paymentStatus"] == "paid" and paid["refundStatus"] in ("none","failed"):
                paid.setdefault("previousCheckIds",[]).append(paid["checkId"])
                paid["checkId"] = check_id
                self.save(paid)
                return self.view(paid)
        pending = next((o for o in existing if o["paymentStatus"] == "pending"),None)
        require(not pending,"PENDING_ORDER_EXISTS","已有待确认订单，请先在我的订单查询原支付结果，避免重复购买。")
        o = {"id": uid("h"), "openid": user["openid"], "checkId": check_id, "product": dict(PRODUCT),
             "platform": platform if platform in ("ios", "android", "windows", "mac", "devtools") else "unknown",
             "paymentStatus": "pending", "deliveryStatus": "waiting", "refundStatus": "none",
             "createdAt": self.now(), "attempts": 0, "paramsIssued": False}
        self.save(o); return self.view(o)

    def own_order(self, user, order_id):
        o = self.s.get("order", order_id)
        require(o and o["openid"] == user["openid"], "ORDER_NOT_FOUND", "订单不存在。", 404)
        return o

    def save(self, o): self.s.put("order", o["id"], o)
    @staticmethod
    def view(o): return {k:v for k,v in o.items() if k not in ("openid", "paramsIssued")}

    def params(self, user, order_id):
        o = self.own_order(user, order_id)
        require(o["paymentStatus"] == "pending", "ORDER_NOT_PENDING", "订单已支付或已关闭，请查看订单。")
        if o["paramsIssued"]:
            self.reconcile(o,True)
            raise Failure("PAYMENT_ALREADY_STARTED","原订单已发起支付，请先查询结果。不会重复创建支付单。")
        self.find_check(user, o["checkId"])
        result = self.p.params(o, user["key"])
        o["paramsIssued"] = True; self.save(o)
        return result

    def reconcile(self, o, force=False, refund_id=None):
        # No client success flag can advance this state. Re-query even paid orders to notice external refunds.
        if not o["paramsIssued"] or o["paymentStatus"] in ("closed", "refunded"): return o
        now = self.now()
        if not force and now-self.last_queries.get(o["id"], 0) < 3000: return o
        q = self.p.query(o); self.last_queries[o["id"]] = now
        require(q.get("order_id") == o["id"], "ORDER_MISMATCH", "微信返回的订单不匹配。", 502)
        status = q.get("status")
        if q.get("order_type") == 7: o["platform"] = "ios"
        require(isinstance(status, int), "ORDER_STATUS_INVALID", "微信订单状态无效。", 502)
        if status in (2,3,4):
            require(q.get("order_fee") == PRODUCT["priceFen"] and q.get("paid_fee", q.get("order_fee")) >= PRODUCT["priceFen"],
                    "AMOUNT_MISMATCH", "实付金额与订单不一致，请联系客服核对。", 502)
            require(q.get("product_id", PRODUCT["id"]) == PRODUCT["id"], "PRODUCT_MISMATCH", "支付商品不匹配。", 502)
            if o["paymentStatus"] == "pending":
                o["paymentStatus"], o["deliveryStatus"] = "paid", "available"
            if o["refundStatus"] == "failed":
                # A failed refund does not silently remove the user's original paid entitlement.
                o["deliveryStatus"] = "available"
        elif status == 5:
            o["refundStatus"], o["deliveryStatus"] = "processing", "held"
        elif status == 8:
            o["paymentStatus"], o["deliveryStatus"], o["refundStatus"] = "refunded", "revoked", "succeeded"
        elif status == 6 and o["paymentStatus"] == "pending":
            o["paymentStatus"] = "closed"
        elif status == 7:
            require(o["paymentStatus"] == "paid", "REFUND_STATE_INVALID", "退款结果与原订单状态不一致。", 502)
            o["refundStatus"], o["deliveryStatus"] = "failed", "available"
        elif status not in (0,1):
            raise Failure("ORDER_STATUS_UNKNOWN", "微信订单状态尚不能确认，请稍后查询。", 502)
        if o["paymentStatus"] != "refunded" and (refund_id or o.get("providerRefundId") or o.get("refundId")) and (refund_id or o["refundStatus"] == "processing"):
            rid=refund_id or o.get("providerRefundId") or o["refundId"]
            refund=self.p.query_refund(o,rid)
            require(refund.get("order_id")==rid and refund.get("order_type") in (1,8),
                    "REFUND_ORDER_MISMATCH","退款单号或类型不匹配。",502)
            require(refund.get("refund_fee")==PRODUCT["priceFen"],"REFUND_AMOUNT_MISMATCH","退款金额尚不能确认。",502)
            o["providerRefundId"]=rid
            if refund.get("status")==8:
                o["paymentStatus"],o["refundStatus"],o["deliveryStatus"]="refunded","succeeded","revoked"
            elif refund.get("status")==7:
                o["refundStatus"],o["deliveryStatus"]="failed","available"
            elif refund.get("status") in (0,1,5):
                o["refundStatus"],o["deliveryStatus"]="processing","held"
            else:
                raise Failure("REFUND_STATUS_UNKNOWN","退款状态尚不能确认，请稍后查询。",502)
        if q.get("left_fee",PRODUCT["priceFen"]) < PRODUCT["priceFen"] and o["paymentStatus"]!="refunded" and o["refundStatus"] in ("none","failed"):
            o["refundStatus"],o["deliveryStatus"]="processing","held"
        self.save(o)
        if status == 2 and o["paymentStatus"] == "paid" and not o.get("deliveryReported") and o["refundStatus"] in ("none", "failed"):
            try:
                self.p.delivered(o)
                o["deliveryReported"] = True
                self.save(o)
            except Failure:
                pass
        return o

    def sweep(self):
        for o in self.s.all("order"):
            if o["paramsIssued"] and o["paymentStatus"] in ("pending", "paid"):
                try: self.reconcile(o, True)
                except Failure: pass

    def get(self, user, order_id, force=False):
        return self.view(self.reconcile(self.own_order(user, order_id), force))

    def orders(self, user):
        # List uses persisted snapshots; opening each order refreshes authoritative state.
        return sorted([self.view(o) for o in self.s.all("order") if o["openid"]==user["openid"]],
                      key=lambda o:o["createdAt"], reverse=True)

    def request_refund(self, user, order_id, reason):
        o = self.reconcile(self.own_order(user, order_id), True)
        require(o["platform"] != "ios", "APPLE_REFUND", "此订单请通过 Apple 购买记录申请退款。")
        require(o["paymentStatus"] == "paid", "REFUND_UNAVAILABLE", "当前订单不能申请退款。")
        if o["refundStatus"] in ("requested", "processing"): return self.view(o)
        require(isinstance(reason, str) and 1 <= len(reason.strip()) <= 200, "REFUND_REASON", "请填写退款原因。")
        o.pop("providerRefundId",None)
        o.update(refundStatus="requested", refundReason=reason.strip(), refundId=uid("r"),
                 refundRequestedAt=self.now(), deliveryStatus="held")
        self.save(o); return self.view(o)

    def approve_refund(self, order_id):
        o = self.s.get("order", order_id)
        require(o and o["platform"] != "ios" and o["refundStatus"] in ("requested", "processing"),
                "REFUND_UNAVAILABLE", "没有待处理的退款申请。")
        try:
            o = self.reconcile(o, True)
        except Failure as e:
            # Ambiguous previous refund submission may have no queryable refund yet.
            # Re-submit only the same refund ID; authoritative original amount is checked below.
            if o["refundStatus"]!="processing" or e.code not in ("WECHAT_REJECTED","WECHAT_UNAVAILABLE","REFUND_QUERY_FAILED"): raise
        if o["refundStatus"] == "succeeded": return self.view(o)
        require(o["platform"]!="ios","APPLE_REFUND","Apple 订单不能由商户发起退款。")
        user_session = next((session for session in reversed(list(self.sessions.values())) if session["openid"]==o["openid"] and session["until"]>self.now()), None)
        require(user_session,"REFUND_LOGIN_REQUIRED","请用户重新打开小程序登录后再处理退款。",409)
        # Persist processing before network: retry reuses same refundId after ambiguous timeout.
        o["refundStatus"] = "processing"; o["deliveryStatus"] = "held"; self.save(o)
        q = self.p.query(o)
        require(q.get("order_id")==o["id"] and q.get("status") in (2,3,4), "REFUND_QUERY", "请先核实微信订单状态。", 502)
        left_fee = q.get("left_fee")
        require(isinstance(left_fee, int) and left_fee >= PRODUCT["priceFen"], "REFUND_AMOUNT", "可退金额不足或未能确认。", 502)
        self.p.refund(o, o["refundId"], left_fee, user_session["key"])
        # API acceptance starts a task; never label refunded until provider confirms final success.
        return self.view(o)

    def continue_install(self, user, order_id):
        o = self.reconcile(self.own_order(user, order_id), True)
        require(o["paymentStatus"] == "paid" and o["refundStatus"] in ("none", "failed"),
                "NO_ENTITLEMENT", "订单暂不可领取，请查看支付或退款状态。")
        self.find_check(user, o["checkId"])
        return {"order": self.view(o), "message": "付款已确认，请回到原电脑页面继续安装，无需再次扫码。"}

    def cancel(self, user, order_id):
        o = self.own_order(user, order_id)
        require(not o["paramsIssued"], "PAYMENT_IN_FLIGHT", "支付已发起，请先查询结果，不能直接关闭订单。")
        require(o["paymentStatus"] == "pending", "ORDER_NOT_PENDING", "订单不能取消。")
        o["paymentStatus"] = "closed"; self.save(o); return self.view(o)

    def pc_status(self, code, token):
        c = self.s.get("check", code)
        require(c and hmac.compare_digest(c["pcHash"], sha(token)), "PC_UNAUTHORIZED", "电脑会话无效。", 403)
        o = max((o for o in self.s.all("order") if o["checkId"]==c["id"]),key=lambda o:o["createdAt"],default=None)
        if o: o = self.reconcile(o)
        return {"check": self.check_view(c), "order": self.view(o) if o else None,
                "canContinue": bool(o and o["paymentStatus"]=="paid" and o["refundStatus"] in ("none","failed") and c["expiresAt"]>self.now())}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # No URL/token/body logging.
    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status); self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def _read_event_body(self, query):
        # Returns the raw event body. Plain mode body is passed through;
        # safe mode decrypts <Encrypt> with EncodingAESKey. The reply format
        # later mirrors the decrypted shape (JSON event -> JSON, XML -> XML).
        length=int(self.headers.get("Content-Length","0"))
        require(0<length<=16384,"INVALID_BODY","回调请求格式不正确。")
        raw_body=self.rfile.read(length)
        if query.get("encrypt_type",[""])[0]!="aes":
            return raw_body
        require(raw_body.lstrip().startswith(b"{"),"INVALID_XML","不支持的消息格式。")
        require(b"<!DOCTYPE" not in raw_body.upper(),"INVALID_XML","不支持的消息格式。")
        envelope=json.loads(raw_body)
        encrypt=envelope.get("Encrypt") if isinstance(envelope,dict) else None
        require(isinstance(encrypt,str) and encrypt,"CALLBACK_ENCRYPT_MISSING","加密回调缺少密文字段。")
        aes_key=os.environ.get("HERMES_CALLBACK_AES_KEY","")
        require(aes_key,"CALLBACK_AESKEY_UNCONFIGURED","服务端未配置加密回调密钥。",503)
        # Failure here fails closed: no success ack is generated for a body
        # that cannot be authenticated as addressed to this AppId.
        return decrypt_callback(encrypt, aes_key, APP_ID)

    def callback(self, method):
        query=parse_qs(urlparse(self.path).query)
        token=os.environ.get("HERMES_CALLBACK_TOKEN","")
        timestamp=query.get("timestamp",[""])[0];nonce=query.get("nonce",[""])[0]
        signature=query.get("signature",[""])[0]
        require(token and timestamp.isdigit() and abs(int(time.time())-int(timestamp))<300,
                "CALLBACK_INVALID","回调验证失败。",403)
        expected=hashlib.sha1("".join(sorted([token,timestamp,nonce])).encode()).hexdigest()
        require(hmac.compare_digest(expected,signature),"CALLBACK_INVALID","回调验证失败。",403)
        if method=="GET":
            raw=query.get("echostr",[""])[0].encode();content_type="text/plain"
        else:
            raw_body=self._read_event_body(query)
            if isinstance(raw_body,str):raw_body=raw_body.encode()
            if raw_body.lstrip().startswith(b"{"):event=json.loads(raw_body)
            else:
                require(b"<!DOCTYPE" not in raw_body.upper(),"INVALID_XML","不支持的消息格式。")
                tree=ElementTree.fromstring(raw_body)
                event={node.tag:node.text or "" for node in tree}
            require(event.get("Event") in ("xpay_goods_deliver_notify","xpay_refund_notify"),
                    "EVENT_UNSUPPORTED","不支持的事件。")
            order_id=(event.get("MchOrderId") if event["Event"]=="xpay_refund_notify" else event.get("OutTradeNo"))
            with self.server.app.s.lock:
                order=self.server.app.s.get("order",order_id)
                require(order,"ORDER_NOT_FOUND","订单不存在。",404)
                supplied=event.get("OpenId")
                require(supplied==order["openid"],"CALLBACK_OWNER_MISMATCH","订单账号不一致。",403)
                updated=self.server.app.reconcile(order,True,event.get("MchRefundId") if event["Event"]=="xpay_refund_notify" else None)
                confirmed = updated["paymentStatus"]=="paid" if event["Event"]=="xpay_goods_deliver_notify" else updated["refundStatus"] in ("succeeded","failed")
                require(confirmed,"CALLBACK_NOT_CONFIRMED","订单结果尚未确认，请重试。",503)
            if raw_body.lstrip().startswith(b"{"):
                raw=b'{"ErrCode":0,"ErrMsg":"success"}';content_type="application/json"
            else:
                raw=b"<xml><ErrCode>0</ErrCode><ErrMsg><![CDATA[success]]></ErrMsg></xml>";content_type="application/xml"
        self.send_response(200);self.send_header("Content-Type",content_type)
        self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(raw)))
        self.end_headers();self.wfile.write(raw)

    def do_GET(self): self.dispatch("GET")
    def do_POST(self): self.dispatch("POST")
    def dispatch(self, method):
        try:
            path = urlparse(self.path).path
            if path == "/wechat/events":
                self.callback(method)
                return
            ip=self.client_address[0];now=time.monotonic()
            with self.server.rate_lock:
                bucket=[t for t in self.server.rate.get(ip,[]) if now-t<60]
                require(len(bucket)<120,"RATE_LIMIT","操作较频繁，请稍后重试。",429)
                bucket.append(now);self.server.rate[ip]=bucket
            length = int(self.headers.get("Content-Length", "0"))
            require(0 <= length <= 16384, "BODY_TOO_LARGE", "请求过大。", 413)
            body = json.loads(self.rfile.read(length)) if length else {}
            require(isinstance(body, dict), "INVALID_BODY", "请求格式不正确。")
            token = self.headers.get("Authorization", "").removeprefix("Bearer ")
            app = self.server.app
            with app.s.lock:
                if path == "/health" and method == "GET": result = {"ok":True,"paymentEnabled":os.getenv("HERMES_PAYMENT_ENABLED")=="1"}
                elif path == "/auth/login" and method == "POST": result = app.login(body.get("code"))
                elif path.startswith("/admin/"):
                    expected = os.getenv("HERMES_ADMIN_TOKEN", "")
                    require(expected and hmac.compare_digest(token, expected), "FORBIDDEN", "无操作权限。", 403)
                    if path == "/admin/checks" and method == "POST": result = app.provision_check(body)
                    elif re.fullmatch(r"/admin/refunds/[A-Za-z0-9]+/approve", path) and method == "POST":
                        result = app.approve_refund(path.split("/")[3])
                    else: raise Failure("NOT_FOUND", "接口不存在。", 404)
                elif re.fullmatch(r"/pc/checks/[A-Za-z0-9_-]+", path) and method == "GET":
                    result = app.pc_status(path.split("/")[-1], token)
                else:
                    user = app.auth(token)
                    if path == "/checks/link" and method == "POST": result = app.link(user, body.get("code", ""))
                    elif path == "/checks/confirm" and method == "POST": result = app.confirm_check(user, body.get("checkId"))
                    elif path == "/orders" and method == "GET": result = app.orders(user)
                    elif path == "/orders" and method == "POST": result = app.create_order(user, body.get("checkId"), body.get("platform"))
                    elif re.fullmatch(r"/orders/[A-Za-z0-9]+(?:/[a-z-]+)?", path):
                        parts=path.split("/"); order_id=parts[2]; action=parts[3] if len(parts)>3 else ""
                        if not action and method=="GET": result=app.get(user,order_id)
                        elif action=="pay-params" and method=="POST": result=app.params(user,order_id)
                        elif action=="confirm" and method=="POST": result=app.get(user,order_id,True)
                        elif action=="refund" and method=="POST": result=app.request_refund(user,order_id,body.get("reason"))
                        elif action=="continue" and method=="POST": result=app.continue_install(user,order_id)
                        elif action=="cancel" and method=="POST": result=app.cancel(user,order_id)
                        else: raise Failure("NOT_FOUND","接口不存在。",404)
                    else: raise Failure("NOT_FOUND","接口不存在。",404)
            self.send_json(result)
        except Failure as e: self.send_json({"code":e.code,"message":str(e)},e.status)
        except (ValueError, TypeError, ElementTree.ParseError): self.send_json({"code":"INVALID_BODY","message":"请求格式不正确。"},400)
        except Exception: self.send_json({"code":"INTERNAL_ERROR","message":"服务暂不可用，请稍后重试。"},500)

def main():
    os.umask(0o077)
    path=os.getenv("HERMES_DB_PATH","./hermes-payments.sqlite")
    os.makedirs(os.path.dirname(os.path.abspath(path)),mode=0o700,exist_ok=True)
    server=ThreadingHTTPServer(("127.0.0.1",int(os.getenv("HERMES_PORT","3021"))),Handler)
    server.app=Service(Store(path),Wechat())
    server.rate={};server.rate_lock=threading.Lock()
    def worker():
        while True:
            time.sleep(300)
            with server.app.s.lock: server.app.sweep()
    threading.Thread(target=worker,daemon=True).start()
    print("Hermes payment service listening on loopback; credentials omitted.")
    server.serve_forever()

if __name__=="__main__": main()
