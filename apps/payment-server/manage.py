"""Local operator commands. Admin token comes from environment, never arguments."""
import argparse, json, os
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="action",required=True)
    approve=sub.add_parser("approve-refund");approve.add_argument("order_id")
    check=sub.add_parser("provision-check");check.add_argument("report");check.add_argument("--out",required=True)
    args=parser.parse_args()
    token=os.environ.get("HERMES_ADMIN_TOKEN")
    if not token:parser.error("HERMES_ADMIN_TOKEN is required in operator environment")
    if args.action=="approve-refund":
        if not args.order_id.isalnum():parser.error("invalid order id")
        path="/admin/refunds/"+args.order_id+"/approve";body={}
    else:
        report=json.loads(Path(args.report).read_text())
        checks=report.get("checks",[])
        if not checks or report.get("overall") not in ("PASS","WARN"):
            parser.error("preflight report must pass")
        if any(c.get("status")=="BLOCK" or (c.get("hard",True) and c.get("status")=="UNKNOWN") for c in checks):
            parser.error("preflight report contains a blocking check")
        body={"status":"PASS","productVersion":"3861473","environment":str(report.get("os_name",""))+" / "+str(report.get("arch",""))}
        path="/admin/checks"
    url="http://127.0.0.1:"+os.environ.get("HERMES_PORT","3021")+path
    req=Request(url,data=json.dumps(body).encode(),headers={"Authorization":"Bearer "+token,"Content-Type":"application/json"})
    try:
        with urlopen(req,timeout=45) as r:data=json.load(r)
    except HTTPError as e:
        data=json.load(e);print(data.get("code","ERROR")+": "+data.get("message","operation failed"));return 1
    if args.action=="provision-check":
        out=Path(args.out)
        fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as f:json.dump(data,f)
        print("Computer session written; keep pcToken private. Code may be passed via scene to pages/check/index.")
    else:
        print("Refund status: "+data["refundStatus"]+"; money is refunded only when provider confirms succeeded.")
    return 0
if __name__=="__main__":raise SystemExit(main())
