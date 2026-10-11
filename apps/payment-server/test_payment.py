import hashlib, json, os, tempfile, threading, time, unittest
from urllib.parse import urlencode
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from payment import Service, Store, Wechat, PRODUCT, Failure, mac, Handler, ThreadingHTTPServer

class FakeWechat:
    def __init__(self): self.status=1; self.fee=990; self.refunds=[]; self.queries=0; self.deliveries=[]; self.refund_status=1
    def login(self,code): return code, "key-"+code
    def params(self,order,key): return {"mode":"short_series_goods","signData":"opaque","paySig":"p","signature":"s"}
    def query(self,order):
        self.queries+=1
        return {"order_id":order["id"],"status":self.status,"order_fee":self.fee,"paid_fee":self.fee,"left_fee":990}
    def delivered(self,order):self.deliveries.append(order["id"]);return {"errcode":0}
    def query_refund(self,order,refund_id):
        return {"order_id":refund_id,"order_type":1,"refund_fee":990,"status":self.refund_status}
    def refund(self,order,refund_id,left,key): self.refunds.append(refund_id);return {"errcode":0}

class Payments(unittest.TestCase):
    def setUp(self):
        self.now=1000000000;self.p=FakeWechat();self.store=Store(":memory:")
        self.app=Service(self.store,self.p,lambda:self.now)
        self.user=self.app.auth(self.app.login("alice")["token"])
        self.other=self.app.auth(self.app.login("bob")["token"])
        self.pc=self.app.provision_check({"status":"PASS","productVersion":PRODUCT["version"],"environment":"test"})
        self.c=self.app.link(self.user,self.pc["code"]);self.app.confirm_check(self.user,self.c["id"])
        self.o=self.app.create_order(self.user,self.c["id"],"android")
    def tearDown(self): self.store.db.close()
    def paid(self):
        self.app.params(self.user,self.o["id"]);self.p.status=2
        return self.app.get(self.user,self.o["id"],True)
    def test_login_secret_not_exposed(self):
        self.assertNotIn("key",self.app.login("alice"))
        self.assertNotIn("key-alice",json.dumps(self.app.orders(self.user)))
    def test_pairing_cannot_be_stolen(self):
        with self.assertRaises(Failure):self.app.link(self.other,self.pc["code"])
    def test_blocked_check_not_provisioned(self):
        with self.assertRaises(Failure):self.app.provision_check({"status":"BLOCK","productVersion":PRODUCT["version"]})
    def test_duplicate_create_reuses_order(self):
        self.assertEqual(self.app.create_order(self.user,self.c["id"],"ios")["id"],self.o["id"])
        self.assertEqual(len(self.app.orders(self.user)),1)
    def test_other_account_cannot_view_or_refund(self):
        for fn in [lambda:self.app.get(self.other,self.o["id"]),lambda:self.app.params(self.other,self.o["id"]),
                   lambda:self.app.request_refund(self.other,self.o["id"],"test")]:
            with self.assertRaises(Failure):fn()
    def test_frontend_success_cannot_grant(self):
        self.app.params(self.user,self.o["id"])
        self.assertEqual(self.app.get(self.user,self.o["id"],True)["paymentStatus"],"pending")
        with self.assertRaises(Failure):self.app.continue_install(self.user,self.o["id"])
    def test_amount_mismatch_keeps_pending(self):
        self.app.params(self.user,self.o["id"]);self.p.status=2;self.p.fee=1
        with self.assertRaises(Failure):self.app.get(self.user,self.o["id"],True)
        self.assertEqual(self.store.get("order",self.o["id"])["paymentStatus"],"pending")
    def test_expired_check_rejects_payment(self):
        self.now+=31*60000
        with self.assertRaises(Failure):self.app.params(self.user,self.o["id"])
    def test_paid_retries_no_second_order(self):
        self.paid()
        a=self.app.continue_install(self.user,self.o["id"])
        b=self.app.continue_install(self.user,self.o["id"])
        self.assertEqual(a["order"]["id"],b["order"]["id"])
        self.assertTrue(self.app.pc_status(self.pc["code"],self.pc["pcToken"])["canContinue"])
    def test_pc_secret_required(self):
        with self.assertRaises(Failure):self.app.pc_status(self.pc["code"],"wrong")
    def test_refund_pending_is_not_success(self):
        self.paid()
        a=self.app.request_refund(self.user,self.o["id"],"无法使用")
        b=self.app.request_refund(self.user,self.o["id"],"重复申请")
        self.assertEqual(a["refundId"],b["refundId"])
        self.assertEqual(a["paymentStatus"],"paid");self.assertEqual(a["refundStatus"],"requested")
        self.assertFalse(self.app.pc_status(self.pc["code"],self.pc["pcToken"])["canContinue"])
        with self.assertRaises(Failure):self.app.continue_install(self.user,self.o["id"])
    def test_refund_approval_idempotent_id_and_final_confirmation(self):
        self.paid();self.app.request_refund(self.user,self.o["id"],"test")
        a=self.app.approve_refund(self.o["id"]);b=self.app.approve_refund(self.o["id"])
        self.assertEqual(self.p.refunds[0],self.p.refunds[1])
        self.assertEqual(b["refundStatus"],"processing");self.assertEqual(b["paymentStatus"],"paid")
        self.p.status=8
        done=self.app.get(self.user,self.o["id"],True)
        self.assertEqual(done["refundStatus"],"succeeded");self.assertEqual(done["deliveryStatus"],"revoked")
        with self.assertRaises(Failure):self.app.continue_install(self.user,self.o["id"])
    def test_external_apple_refund_revokes(self):
        self.paid();self.p.status=8
        self.assertEqual(self.app.get(self.user,self.o["id"],True)["paymentStatus"],"refunded")
    def test_ios_cannot_request_merchant_refund(self):
        self.paid();o=self.store.get("order",self.o["id"]);o["platform"]="ios";self.app.save(o)
        with self.assertRaises(Failure) as caught:self.app.request_refund(self.user,o["id"],"test")
        self.assertEqual(caught.exception.code,"APPLE_REFUND")
    def test_refund_failed_restores_paid_entitlement(self):
        self.paid();self.app.request_refund(self.user,self.o["id"],"test");self.p.status=7
        o=self.app.get(self.user,self.o["id"],True)
        self.assertEqual(o["paymentStatus"],"paid");self.assertEqual(o["refundStatus"],"failed")
        self.assertEqual(o["deliveryStatus"],"available")
    def test_cancel_after_payment_start_rejected(self):
        self.app.params(self.user,self.o["id"])
        with self.assertRaises(Failure):self.app.cancel(self.user,self.o["id"])
    def test_persistence_preserves_pending_refund(self):
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/"pay.sqlite";s=Store(str(p));s.put("order","x",{"refundStatus":"processing"})
            s.db.close();s2=Store(str(p));self.assertEqual(s2.get("order","x")["refundStatus"],"processing");s2.db.close()

    def test_delivery_notification_only_once(self):
        self.paid();self.app.get(self.user,self.o["id"],True);self.app.sweep()
        self.assertEqual(self.p.deliveries,[self.o["id"]])
    def test_background_refund_reconciles_without_client_open(self):
        self.paid();self.p.status=8;self.app.sweep()
        self.assertEqual(self.store.get("order",self.o["id"])["deliveryStatus"],"revoked")
    def test_unknown_provider_state_fails_closed(self):
        self.app.params(self.user,self.o["id"]);self.p.status=99
        with self.assertRaises(Failure):self.app.get(self.user,self.o["id"],True)
        self.assertEqual(self.store.get("order",self.o["id"])["paymentStatus"],"pending")

    def test_fresh_check_recovers_paid_order_without_new_charge(self):
        self.paid();self.now+=31*60000
        pc=self.app.provision_check({"status":"PASS","productVersion":"3861473"})
        c=self.app.link(self.user,pc["code"]);self.app.confirm_check(self.user,c["id"])
        restored=self.app.create_order(self.user,c["id"],"android")
        self.assertEqual(restored["id"],self.o["id"]);self.assertEqual(len(self.app.orders(self.user)),1)
        self.assertTrue(self.app.pc_status(pc["code"],pc["pcToken"])["canContinue"])
    def test_repeat_pay_params_does_not_create_second_attempt(self):
        self.app.params(self.user,self.o["id"])
        with self.assertRaises(Failure) as caught:self.app.params(self.user,self.o["id"])
        self.assertEqual(caught.exception.code,"PAYMENT_ALREADY_STARTED")
    def test_new_check_does_not_duplicate_pending_payment(self):
        pc=self.app.provision_check({"status":"PASS","productVersion":"3861473"})
        c=self.app.link(self.user,pc["code"]);self.app.confirm_check(self.user,c["id"])
        with self.assertRaises(Failure) as caught:self.app.create_order(self.user,c["id"],"android")
        self.assertEqual(caught.exception.code,"PENDING_ORDER_EXISTS")
    def test_refunding_order_not_replaced_by_new_purchase(self):
        self.paid();self.app.request_refund(self.user,self.o["id"],"test")
        pc=self.app.provision_check({"status":"PASS","productVersion":"3861473"})
        c=self.app.link(self.user,pc["code"]);self.app.confirm_check(self.user,c["id"])
        with self.assertRaises(Failure) as caught:self.app.create_order(self.user,c["id"],"android")
        self.assertEqual(caught.exception.code,"REFUND_IN_PROGRESS")

    def test_merchant_debit_not_user_refund_success(self):
        self.paid();self.app.request_refund(self.user,self.o["id"],"test");self.app.approve_refund(self.o["id"])
        self.p.refund_status=5
        pending=self.app.get(self.user,self.o["id"],True)
        self.assertEqual(pending["paymentStatus"],"paid");self.assertEqual(pending["refundStatus"],"processing")
        self.assertEqual(pending["deliveryStatus"],"held")
        self.p.refund_status=8
        done=self.app.get(self.user,self.o["id"],True)
        self.assertEqual(done["paymentStatus"],"refunded");self.assertEqual(done["deliveryStatus"],"revoked")
    def test_refund_query_uses_refund_order_id(self):
        self.paid();r=self.app.request_refund(self.user,self.o["id"],"test");self.app.approve_refund(self.o["id"])
        self.p.refund_status=8
        self.assertEqual(self.app.get(self.user,self.o["id"],True)["refundStatus"],"succeeded")
    def test_refund_operator_requires_fresh_user_login(self):
        self.paid();self.app.request_refund(self.user,self.o["id"],"test");self.now+=3600001
        with self.assertRaises(Failure) as caught:self.app.approve_refund(self.o["id"])
        self.assertEqual(caught.exception.code,"REFUND_LOGIN_REQUIRED")

class Signatures(unittest.TestCase):
    def test_hmac_known_vector(self):
        self.assertEqual(mac("\x0b"*20,"Hi There"),"b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7")
    def test_params_only_server_price_and_opaque_body(self):
        c={"HERMES_PAYMENT_ENABLED":"1","HERMES_APP_SECRET":"not-real","HERMES_VP_APP_KEY":"test"}
        p=Wechat(c);r=p.params({"id":"h123456789","checkId":"c"},"session")
        d=json.loads(r["signData"]);self.assertEqual(d["goodsPrice"],990);self.assertEqual(d["offerId"],"1450674694")
        self.assertEqual(d["productId"],"hermes_install_990");self.assertNotIn("platform",d)
        self.assertNotIn("session",r["signData"]);self.assertEqual(len(r["paySig"]),64)
    def test_disabled_provider_no_network(self):
        p=Wechat({},lambda *args:self.fail("network called"))
        with self.assertRaises(Failure):p.params({"id":"h","checkId":"c"},"key")
    def test_signed_query_body_not_reserialized(self):
        seen=[]
        def transport(url,body):
            if "/stable_token" in url:return {"access_token":"test","expires_in":7200}
            seen.append((url,body));return {"order":{"order_id":"h","status":1}}
        c={"HERMES_PAYMENT_ENABLED":"1","HERMES_APP_SECRET":"a","HERMES_VP_APP_KEY":"k"}
        p=Wechat(c,transport);p.query({"id":"h","openid":"u"})
        url,body=seen[0];self.assertIn("pay_sig="+mac("k","/xpay/query_order&"+body),url)
        self.assertEqual(json.loads(body),{"openid":"u","order_id":"h","env":0})
    def test_provider_error_sanitized(self):
        with self.assertRaises(Failure) as caught:Wechat.http("https://invalid.invalid/?secret=do-not-expose")
        self.assertNotIn("secret",str(caught.exception))

    def test_official_signing_vector(self):
        body='{"openid": "xxx", "user_ip": "127.0.0.1", "env": 0}'
        self.assertEqual(mac("12345","/xpay/query_user_balance&"+body),"c37809f27c6d7fd1837ad2500a04512b66b34fd793a39a385fade56dca89a4b5")
        self.assertEqual(mac("9hAb/NEYUlkaMBEsmFgzig==",body),"089d9e8dc5d308977360c4b79ec600a93d736802802a807d634192328032f6c7")
    def test_refund_wire_uses_two_signatures(self):
        seen=[]
        def transport(url,body):
            if "/stable_token" in url:return {"access_token":"token"}
            seen.append((url,body));return {"errcode":0}
        p=Wechat({"HERMES_PAYMENT_ENABLED":"1","HERMES_APP_SECRET":"a","HERMES_VP_APP_KEY":"key"},transport)
        p.refund({"id":"h1","openid":"alice"},"r1",990,"session")
        url,body=seen[0]
        self.assertIn("pay_sig="+mac("key","/xpay/refund_order&"+body),url)
        self.assertIn("signature="+mac("session",body),url)
        self.assertEqual(json.loads(body)["refund_order_id"],"r1")
    def test_delivery_wire_only_documented_fields(self):
        seen=[]
        def transport(url,body):
            if "/stable_token" in url:return {"access_token":"token"}
            seen.append((url,body));return {"errcode":0}
        p=Wechat({"HERMES_PAYMENT_ENABLED":"1","HERMES_APP_SECRET":"a","HERMES_VP_APP_KEY":"key"},transport)
        p.delivered({"id":"h1","openid":"alice"})
        url,body=seen[0]
        self.assertNotIn("pay_sig",url);self.assertEqual(json.loads(body),{"order_id":"h1","env":0})

class HTTPBoundaries(unittest.TestCase):
    def setUp(self):
        self.store=Store(":memory:");self.app=Service(self.store,FakeWechat())
        self.server=ThreadingHTTPServer(("127.0.0.1",0),Handler);self.server.app=self.app;self.server.rate={};self.server.rate_lock=threading.Lock()
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.store.db.close()
    def call(self,path,body=None,token=""):
        req=Request("http://127.0.0.1:"+str(self.server.server_port)+path,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
        try:
            with urlopen(req,timeout=3) as res:return res.status,json.load(res)
        except HTTPError as e:return e.code,json.load(e)
    def test_unauthed_orders_rejected_and_admin_separate(self):
        status,data=self.call("/orders");self.assertEqual(status,401)
        token=self.call("/auth/login",{"code":"alice"})[1]["token"]
        with patch.dict(os.environ,{"HERMES_ADMIN_TOKEN":"admin-secret"}):
            self.assertEqual(self.call("/admin/checks",{"status":"PASS","productVersion":"3861473"},token)[0],403)
            self.assertEqual(self.call("/admin/checks",{"status":"PASS","productVersion":"3861473"},"admin-secret")[0],200)
    def test_client_price_and_paid_flag_ignored(self):
        token=self.call("/auth/login",{"code":"alice"})[1]["token"]
        pc=self.app.provision_check({"status":"PASS","productVersion":"3861473"})
        c=self.call("/checks/link",{"code":pc["code"]},token)[1]
        self.call("/checks/confirm",{"checkId":c["id"]},token)
        status,o=self.call("/orders",{"checkId":c["id"],"platform":"android","priceFen":1,"paymentStatus":"paid"},token)
        self.assertEqual(status,200);self.assertEqual(o["product"]["priceFen"],990);self.assertEqual(o["paymentStatus"],"pending")

    def event(self,event,valid=True):
        stamp=str(int(time.time()));nonce="test"
        sig=hashlib.sha1("".join(sorted(["callback-test",stamp,nonce])).encode()).hexdigest()
        q=urlencode({"timestamp":stamp,"nonce":nonce,"signature":sig if valid else "bad"})
        return self.call("/wechat/events?"+q,event)
    def fixture_order(self):
        u=self.app.auth(self.app.login("alice")["token"])
        c=self.app.provision_check({"status":"PASS","productVersion":"3861473"})
        linked=self.app.link(u,c["code"]);self.app.confirm_check(u,linked["id"])
        o=self.app.create_order(u,linked["id"],"android");self.app.params(u,o["id"])
        return o
    def test_unverified_webhook_cannot_change_payment(self):
        o=self.fixture_order()
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            self.assertEqual(self.event({"Event":"xpay_goods_deliver_notify","OutTradeNo":o["id"]},False)[0],403)
        self.assertEqual(self.store.get("order",o["id"])["paymentStatus"],"pending")
    def test_signed_callback_still_queries_provider(self):
        o=self.fixture_order()
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            self.assertEqual(self.event({"Event":"xpay_goods_deliver_notify","OutTradeNo":o["id"],"OpenId":"alice","paid":True})[0],503)
        self.assertEqual(self.store.get("order",o["id"])["paymentStatus"],"pending")
    def test_encrypted_callback_not_silently_acknowledged(self):
        stamp=str(int(time.time()));nonce="x"
        sig=hashlib.sha1("".join(sorted(["callback-test",stamp,nonce])).encode()).hexdigest()
        q=urlencode({"timestamp":stamp,"nonce":nonce,"signature":sig,"encrypt_type":"aes"})
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            self.assertEqual(self.call("/wechat/events?"+q,{"Encrypt":"opaque"})[0],501)

    def test_valid_delivery_and_refund_callbacks_confirm_provider_state(self):
        o=self.fixture_order()
        stamp=str(int(time.time()));nonce="positive"
        sig=hashlib.sha1("".join(sorted(["callback-test",stamp,nonce])).encode()).hexdigest()
        q=urlencode({"timestamp":stamp,"nonce":nonce,"signature":sig})
        self.app.p.status=2
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            for event,status in [("xpay_goods_deliver_notify","paid"),("xpay_refund_notify","refunded")]:
                if event=="xpay_refund_notify":self.app.p.status=8
                raw=json.dumps({"Event":event,"OutTradeNo":o["id"],"MchOrderId":o["id"],"OpenId":"alice"}).encode()
                req=Request("http://127.0.0.1:"+str(self.server.server_port)+"/wechat/events?"+q,data=raw)
                with urlopen(req,timeout=3) as res:
                    self.assertEqual(res.status,200);self.assertEqual(json.load(res)["ErrCode"],0)
                self.assertEqual(self.store.get("order",o["id"])["paymentStatus"],status)
        self.assertEqual(len(self.app.p.deliveries),1)
    def test_invalid_xml_does_not_crash_callback(self):
        stamp=str(int(time.time()));nonce="xml"
        sig=hashlib.sha1("".join(sorted(["callback-test",stamp,nonce])).encode()).hexdigest()
        q=urlencode({"timestamp":stamp,"nonce":nonce,"signature":sig})
        req=Request("http://127.0.0.1:"+str(self.server.server_port)+"/wechat/events?"+q,data=b"<xml>")
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            with self.assertRaises(HTTPError) as caught:urlopen(req,timeout=3)
        self.assertEqual(caught.exception.code,400)

    def test_refund_notification_uses_official_merchant_order_id(self):
        o=self.fixture_order();u=self.app.auth(self.app.login("alice")["token"])
        self.app.p.status=2;self.app.get(u,o["id"],True)
        self.app.p.refund_status=8
        stamp=str(int(time.time()));nonce="refund"
        sig=hashlib.sha1("".join(sorted(["callback-test",stamp,nonce])).encode()).hexdigest()
        q=urlencode({"timestamp":stamp,"nonce":nonce,"signature":sig})
        raw=json.dumps({"Event":"xpay_refund_notify","MchOrderId":o["id"],"MchRefundId":"r123456789","OpenId":"alice","FromUserName":"wechat_official"}).encode()
        req=Request("http://127.0.0.1:"+str(self.server.server_port)+"/wechat/events?"+q,data=raw)
        with patch.dict(os.environ,{"HERMES_CALLBACK_TOKEN":"callback-test"}):
            with urlopen(req,timeout=3) as res:self.assertEqual(json.load(res)["ErrCode"],0)
        self.assertEqual(self.store.get("order",o["id"])["paymentStatus"],"refunded")

if __name__=="__main__":unittest.main()
