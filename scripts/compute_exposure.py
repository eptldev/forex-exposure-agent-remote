"""Compute forex exposure from the input sheet and rates.json.

Writes output/work/exposure.json (metrics and tables) and the HTML workbook in output/.
Convention: payables, so a RISE in INR cost vs booked is an additional cost (positive), a fall is a saving.
Hedged = 'Y' items are assumed fully covered at the booked rate, so they carry no open exposure.
The workbook is plain HTML (tables only, no embedded images) rather than .xlsx, so it is exact
text that can be uploaded to Google Drive without the binary-transcription risk of base64.
"""
import argparse, glob, json
import pandas as pd
import common
from common import log, ROOT, WORK, cr, signed_cr, rs, group_indian

REQ = ["Payment ID", "Vendor", "Country", "Invoice No", "Invoice Date", "Due Date", "Currency", "Amount (FC)", "Booked Rate (INR per 1 FC)", "Expenditure Head", "Hedged (Y/N)", "Late Interest % pa"]
BUCKETS = ["Overdue", "Due in 0-30 days", "Due in 31-60 days", "Due in 61-90 days", "Due after 90 days"]

def bucket(d):
    return BUCKETS[0] if d < 0 else BUCKETS[1] if d <= 30 else BUCKETS[2] if d <= 60 else BUCKETS[3] if d <= 90 else BUCKETS[4]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--input")
    a = ap.parse_args()
    path = a.input or sorted(glob.glob(str(ROOT / "input" / "*.xlsx")))[-1]
    rj = json.load(open(WORK / "rates.json")); rates = rj["rates"]
    ref = pd.Timestamp(common.now().date())
    raw = pd.read_excel(path, sheet_name=0)
    raw.columns = [str(c).strip() for c in raw.columns]
    missing = [c for c in REQ if c not in raw.columns]
    if missing:
        log(f"Input is missing required columns: {missing}", "ERROR"); raise SystemExit(1)
    log(f"Loaded {len(raw)} rows from {path.split('/')[-1]}")
    df = raw.copy()
    df["Currency"] = df["Currency"].astype(str).str.strip().str.upper()
    df["Hedged (Y/N)"] = df["Hedged (Y/N)"].astype(str).str.strip().str.upper().str[:1]
    for c in ("Invoice Date", "Due Date"): df[c] = pd.to_datetime(df[c], errors="coerce", dayfirst=True)
    issues = []
    def flag(idx, why):
        issues.append({"Payment ID": df.at[idx, "Payment ID"], "Vendor": df.at[idx, "Vendor"], "Invoice No": df.at[idx, "Invoice No"], "Issue": why, "Action": "Excluded from calculations"})
        log(f"Excluded {df.at[idx,'Payment ID']}: {why}", "WARN")
    ok = pd.Series(True, index=df.index)
    for i in df.index:
        amt = pd.to_numeric(df.at[i, "Amount (FC)"], errors="coerce"); br = pd.to_numeric(df.at[i, "Booked Rate (INR per 1 FC)"], errors="coerce")
        if pd.isna(amt) or amt <= 0: flag(i, "Amount missing or not positive"); ok[i] = False
        elif pd.isna(br) or br <= 0: flag(i, "Booked rate missing or not positive"); ok[i] = False
        elif pd.isna(df.at[i, "Due Date"]): flag(i, "Due date missing"); ok[i] = False
        elif pd.isna(df.at[i, "Invoice Date"]): flag(i, "Invoice date missing"); ok[i] = False
        elif df.at[i, "Due Date"] < df.at[i, "Invoice Date"]: flag(i, "Due date is before invoice date"); ok[i] = False
        elif df.at[i, "Currency"] not in rates and df.at[i, "Currency"] != "INR": flag(i, f"No rate available for {df.at[i,'Currency']}"); ok[i] = False
    dup = df[ok].duplicated(subset=["Vendor", "Invoice No"], keep="first")
    for i in dup[dup].index: flag(i, "Duplicate of an earlier row (same vendor and invoice number)"); ok[i] = False
    d = df[ok].copy()
    for c in ("Amount (FC)", "Booked Rate (INR per 1 FC)", "Late Interest % pa"): d[c] = pd.to_numeric(d[c], errors="coerce")
    d["Live Rate"] = d["Currency"].map(rates)
    d["Booked INR"] = d["Amount (FC)"] * d["Booked Rate (INR per 1 FC)"]
    d["Live INR"] = d["Amount (FC)"] * d["Live Rate"]
    d["Additional cost INR"] = d["Live INR"] - d["Booked INR"]
    d["Days to due"] = (d["Due Date"] - ref).dt.days
    d["Bucket"] = d["Days to due"].map(bucket)
    d["Days overdue"] = (-d["Days to due"]).clip(lower=0)
    d["Accrued late interest FC"] = d["Amount (FC)"] * d["Late Interest % pa"] / 100 * d["Days overdue"] / 365
    d["Accrued late interest INR"] = d["Accrued late interest FC"] * d["Live Rate"]
    d["Hedged"] = d["Hedged (Y/N)"].eq("Y")
    d["Open live INR"] = d["Live INR"].where(~d["Hedged"], 0.0)
    d["Open additional cost INR"] = d["Additional cost INR"].where(~d["Hedged"], 0.0)
    log(f"{len(d)} valid rows, {int((~ok).sum())} excluded")
    # by currency
    g = d.groupby("Currency")
    cur = pd.DataFrame({"Items": g.size(), "FC": g["Amount (FC)"].sum(), "Booked": g["Booked INR"].sum(), "Live": g["Live INR"].sum(), "Delta": g["Additional cost INR"].sum(), "Open": g["Open live INR"].sum(), "OpenDelta": g["Open additional cost INR"].sum()})
    cur["BookedRate"] = cur["Booked"] / cur["FC"]; cur["LiveRate"] = cur.index.map(rates)
    cur = cur.sort_values("Delta", key=abs, ascending=False)
    tot_b, tot_l = d["Booked INR"].sum(), d["Live INR"].sum(); delta = tot_l - tot_b
    unh, hed = d.loc[~d["Hedged"], "Live INR"].sum(), d.loc[d["Hedged"], "Live INR"].sum()
    od = d[d["Bucket"] == BUCKETS[0]]
    ag = d.groupby("Bucket").agg(Items=("Payment ID", "size"), Live=("Live INR", "sum"), Open=("Open live INR", "sum")).reindex(BUCKETS).fillna(0)
    top = d.groupby("Vendor").agg(Currency=("Currency", "first"), Items=("Payment ID", "size"), Live=("Live INR", "sum"), Delta=("Additional cost INR", "sum"), Open=("Open additional cost INR", "sum")).sort_values("Open", key=abs, ascending=False).head(5)
    sens = [(p, unh * p / 100) for p in (1, 2, 5)]
    tc = cur.index[0]
    word = "additional cost" if delta >= 0 else "saving"
    M = {
        "reference_date": ref.strftime("%d-%m-%Y"), "run_time": common.now().strftime("%d-%m-%Y %H:%M IST"),
        "rate_status": rj["status"], "rate_source": rj["source"], "rate_date": str(rj["rate_date"]),
        "input_file": path.split("/")[-1], "n_loaded": str(len(raw)), "n_valid": str(len(d)), "n_excluded": str(int((~ok).sum())),
        "n_currencies": str(d["Currency"].nunique()), "n_vendors": str(d["Vendor"].nunique()),
        "booked_total": cr(tot_b), "live_total": cr(tot_l), "net_delta": signed_cr(delta), "net_delta_abs": cr(abs(delta)),
        "net_delta_pct": f"{delta / tot_b * 100:+.2f}%", "delta_word": word,
        "unhedged_live": cr(unh), "hedged_live": cr(hed), "unhedged_pct": f"{unh / tot_l * 100:.1f}%",
        "open_delta": signed_cr(d["Open additional cost INR"].sum()),
        "overdue_count": str(len(od)), "overdue_live": cr(od["Live INR"].sum()),
        "late_interest": rs(d["Accrued late interest INR"].sum()), "late_interest_lakh": f"Rs {d['Accrued late interest INR'].sum() / 1e5:,.2f} lakh",
        "top_currency": tc, "top_currency_delta": signed_cr(cur.loc[tc, "Delta"]),
        "sens_1": cr(sens[0][1]), "sens_2": cr(sens[1][1]), "sens_5": cr(sens[2][1]),
        "rate_status_note": {"LIVE": "Live market rates.", "FALLBACK": "WARNING: fallback sample rates were used because live sources could not be reached. These figures are NOT live."}.get(rj["status"], "WARNING: test rates, not live market rates."),
    }
    def money(x): return cr(x)
    T = {
        "currency_summary": {"head": ["Currency", "Items", "Amount (FC)", "Booked rate", "Live rate", "Booked (Cr)", "Live (Cr)", "Add. cost (Cr)"],
            "rows": [[c, str(int(r.Items)), group_indian(r.FC), f"{r.BookedRate:.4f}", f"{r.LiveRate:.4f}", f"{r.Booked / 1e7:,.2f}", f"{r.Live / 1e7:,.2f}", f"{r.Delta / 1e7:+,.2f}"] for c, r in cur.iterrows()]
                    + [["Total", str(len(d)), "", "", "", f"{tot_b / 1e7:,.2f}", f"{tot_l / 1e7:,.2f}", f"{delta / 1e7:+,.2f}"]], "align": "LRRRRRRR", "boldlast": True},
        "aging": {"head": ["Due bucket", "Items", "Live value (Cr)", "Open (unhedged) (Cr)"],
            "rows": [[b, str(int(r.Items)), f"{r.Live / 1e7:,.2f}", f"{r.Open / 1e7:,.2f}"] for b, r in ag.iterrows()], "align": "LRRR"},
        "top_vendors": {"head": ["Vendor", "Ccy", "Items", "Live value (Cr)", "Open add. cost (Cr)"],
            "rows": [[v, r.Currency, str(int(r.Items)), f"{r.Live / 1e7:,.2f}", f"{r.Open / 1e7:+,.2f}"] for v, r in top.iterrows()], "align": "LLRRR"},
        "sensitivity": {"head": ["INR weakens by", "Additional cost on open exposure"], "rows": [[f"{p}%", cr(v)] for p, v in sens], "align": "LR"},
        "rates": {"head": ["Currency", "Live rate (INR per 1 unit)"], "rows": [[c, f"{r:.4f}"] for c, r in rates.items()], "align": "LR"},
        "data_issues": {"head": ["Payment ID", "Vendor", "Invoice No", "Issue", "Action"],
            "rows": [[i["Payment ID"], i["Vendor"], str(i["Invoice No"]), i["Issue"], i["Action"]] for i in issues] or [["None", "", "", "No data issues found", ""]], "align": "LLLLL"},
    }
    chart = {"delta_by_currency": {c: float(v) / 1e7 for c, v in cur["Delta"].items()}, "aging": {b: [float(r.Open) / 1e7, float(r.Live - r.Open) / 1e7] for b, r in ag.iterrows()}}
    json.dump({"metrics": M, "tables": T, "charts": chart}, open(WORK / "exposure.json", "w"), indent=2)
    # workbook (plain HTML: one section per sheet, tables only, no embedded images)
    stamp = common.now().strftime("%d%m%Y%H%M%S")
    out = ROOT / "output" / f"{stamp}-forex-exposure-workbook.html"
    style = (
        "body{font-family:Helvetica,Arial,sans-serif;color:#1F2A1E;max-width:1100px;margin:24px auto;padding:0 16px}"
        "h1{font-size:18px}h2{font-size:13px;color:#4F6F48;border-bottom:1px solid #D5DDD2;padding-bottom:3px;margin-top:22px}"
        "table{border-collapse:collapse;width:100%;margin:6px 0;font-size:10.5px}"
        "th{background:#4F6F48;color:#fff;text-align:left;padding:4px 6px;white-space:nowrap}"
        "td{padding:4px 6px;border-bottom:1px solid #D5DDD2;white-space:nowrap}"
        "tr:nth-child(even) td{background:#EEF3EC}"
    )
    def esc(x): return str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    def df_html(frame): return frame.to_html(index=False, border=0, escape=True, na_rep="")
    sections = [("summary", pd.DataFrame(list(M.items()), columns=["Metric", "Value"]))]
    for k in ("currency_summary", "aging", "top_vendors", "sensitivity", "rates", "data_issues"):
        sections.append((k.replace("_", " "), pd.DataFrame(T[k]["rows"], columns=T[k]["head"])))
    cols = ["Payment ID", "Vendor", "Currency", "Amount (FC)", "Booked Rate (INR per 1 FC)", "Live Rate", "Booked INR", "Live INR", "Additional cost INR", "Due Date", "Days to due", "Bucket", "Hedged", "Late Interest % pa", "Accrued late interest INR"]
    sections.append(("line detail", d[cols]))
    body = "".join(f"<h2>{esc(name)}</h2>{df_html(frame)}" for name, frame in sections)
    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Forex Exposure Workbook</title>"
        f"<style>{style}</style></head><body>"
        f"<h1>Forex Exposure Workbook — {M['reference_date']}</h1>{body}</body></html>"
    )
    out.write_text(html, encoding="utf-8")
    log(f"Workbook written: {out.name} ({out.stat().st_size} bytes)")
    log(f"Net {word} vs booked: {M['net_delta']} ({M['net_delta_pct']}); unhedged live value {M['unhedged_live']}; overdue {M['overdue_count']} items")
    print(json.dumps(M, indent=1))

if __name__ == "__main__":
    main()
