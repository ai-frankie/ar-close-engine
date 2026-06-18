"""
Regenerate GL.csv so the subledger->GL breaks are DISCOVERABLE:
3 journal entries posted to AR control (1200) with NO invoice reference
(the real audit red flag). Net effect = -1,650 vs subledger, so totals are
unchanged; now a recon can FIND the items instead of being told them.
AR_Aging.csv is left untouched. Run: python regen_gl.py
"""
import csv, os, random
random.seed(7)
D = os.path.dirname(os.path.abspath(__file__))

def fnum(x):
    try: return float(str(x).replace(",", ""))
    except: return None
def main():
    aging = list(csv.DictReader(open(os.path.join(D,"AR_Aging.csv"),encoding="utf-8")))
    subledger = round(sum(fnum(a["Open_Balance"]) or 0 for a in aging), 2)

    rows=[]; eid=500000
    def add(acct,name,desc,dr,cr,src,ref):
        nonlocal eid; eid+=1
        rows.append({"Entry_ID":f"JE{eid}","Date":"2026-06-15","Period":"2026-06",
            "Account_Number":acct,"Account_Name":name,"Description":desc,
            "Debit":round(dr,2) if dr else "","Credit":round(cr,2) if cr else "",
            "Source":src,"Invoice_Ref":ref})

    # clean opening AR (matches subledger) — HAS a reference, so not flagged
    add("1200","Accounts Receivable","Opening AR control (agrees to subledger)",subledger,0,"Opening","OPENING-AR")
    add("3000","Opening Balance Equity","Opening AR offset",0,subledger,"Opening","OPENING-AR")
    # allowance opening
    add("3000","Opening Balance Equity","Opening allowance offset",18000,0,"Opening","OPENING-ALW")
    add("1210","Allowance for Doubtful Accounts","Opening allowance (contra-AR)",0,18000,"Opening","OPENING-ALW")

    # --- the 3 DISCOVERABLE breaks: posted to 1200 with BLANK Invoice_Ref ---
    # +500 manual reclass error (belongs in AP)
    add("1200","Accounts Receivable","Manual JE - reclass error, belongs in AP (2000)",500,0,"Manual JE","")
    add("2000","Accounts Payable","Offset for misposted reclass",0,500,"Manual JE","")
    # -3400 unapplied cash (received, not applied in subledger)
    add("1000","Cash","Customer cash receipt (unapplied in subledger)",3400,0,"Cash Receipt","")
    add("1200","Accounts Receivable","Unapplied cash posted to AR control",0,3400,"Cash Receipt","")
    # +1250 credit-memo accrual posted to AR in error
    add("1200","Accounts Receivable","Credit memo accrual posted to AR in error",1250,0,"Manual JE","")
    add("4000","Revenue","Offset for erroneous credit memo accrual",0,1250,"Manual JE","")
    # net 1200 = subledger +500 -3400 +1250 = subledger -1650  (variance vs subledger = -1650)

    # --- fill to ~500 rows with generic balanced JEs (never touch 1200) ---
    COA=[("1000","Cash"),("1100","Inventory"),("2000","Accounts Payable"),("4000","Revenue"),
         ("5000","COGS"),("6000","Salaries Expense"),("6100","Rent Expense"),("6300","Marketing")]
    descs=["Vendor bill","Customer sale","Payroll run","Rent","Ad spend","Inventory purchase","Accrual","Bank transfer"]
    while len(rows) < 500:
        amt=round(random.uniform(200,40000),2); a1=random.choice(COA); a2=random.choice([x for x in COA if x!=a1])
        d=random.choice(descs); ref=f"DOC-{random.randint(10000,99999)}"
        add(a1[0],a1[1],d,amt,0,"Subledger",ref)
        if len(rows)<500: add(a2[0],a2[1],d,0,amt,"Subledger",ref)
    rows=rows[:500]

    fields=["Entry_ID","Date","Period","Account_Number","Account_Name","Description","Debit","Credit","Source","Invoice_Ref"]
    with open(os.path.join(D,"GL.csv"),"w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

    dr=round(sum(r["Debit"] for r in rows if isinstance(r["Debit"],(int,float))),2)
    cr=round(sum(r["Credit"] for r in rows if isinstance(r["Credit"],(int,float))),2)
    ar=round(sum((r["Debit"] if isinstance(r["Debit"],(int,float)) else 0)-(r["Credit"] if isinstance(r["Credit"],(int,float)) else 0) for r in rows if r["Account_Number"]=="1200"),2)
    flagged=[r for r in rows if r["Account_Number"]=="1200" and r["Invoice_Ref"]==""]
    print(f"GL rows={len(rows)} balanced={abs(dr-cr)<0.01} (DR={dr:,.2f} CR={cr:,.2f})")
    print(f"AR-1200 net={ar:,.2f}  subledger={subledger:,.2f}  variance={ar-subledger:,.2f}")
    print(f"discoverable breaks (1200, no Invoice_Ref): {len(flagged)} rows, net {sum((r['Debit'] if isinstance(r['Debit'],(int,float)) else 0)-(r['Credit'] if isinstance(r['Credit'],(int,float)) else 0) for r in flagged):,.2f}")


if __name__ == "__main__":
    main()
