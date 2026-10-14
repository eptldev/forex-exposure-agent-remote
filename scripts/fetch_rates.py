"""Fetch live INR exchange rates from public APIs (external call).

Usage: python3 scripts/fetch_rates.py [--input path.xlsx] [--allow-fallback]
Writes output/work/rates.json. Exit codes: 0 = live rates, 2 = fallback rates used, 1 = failed.
Rates are INR per 1 unit of the foreign currency. Sources are ECB reference rates (via
Frankfurter) and a second public aggregator. These are NOT RBI reference rates.
"""
import argparse, glob, json, os, sys, urllib.request, urllib.error
import openpyxl
import common
from common import log, ROOT, WORK

def http_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "forex-exposure-agent/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode()), r.status

def currencies_from_input(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    rows = ws.iter_rows(values_only=True)
    hdr = [str(h or "").strip() for h in next(rows)]
    i = hdr.index("Currency")
    return sorted({str(r[i]).strip().upper() for r in rows if r[i] and str(r[i]).strip()} - {"INR"})

def frankfurter(ccys):
    out, date = {}, None
    for c in ccys:
        url = f"https://api.frankfurter.dev/v1/latest?base={c}&symbols=INR"
        d, status = http_json(url)
        log(f"GET {url} -> HTTP {status}")
        out[c] = float(d["rates"]["INR"]); date = d.get("date", date)
    return out, date, "Frankfurter (ECB reference rates)"

def er_api(ccys):
    url = "https://open.er-api.com/v6/latest/USD"
    d, status = http_json(url)
    log(f"GET {url} -> HTTP {status}")
    r = d["rates"]
    out = {c: r["INR"] / r[c] for c in ccys}
    return out, (d.get("time_last_update_utc") or "")[:16], "open.er-api.com (aggregated market rates)"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input"); ap.add_argument("--allow-fallback", action="store_true")
    a = ap.parse_args()
    path = a.input or sorted(glob.glob(str(ROOT / "input" / "*.xlsx")))[-1]
    ccys = currencies_from_input(path)
    log(f"Currencies to fetch (vs INR): {', '.join(ccys)}")
    WORK.mkdir(parents=True, exist_ok=True)
    for fn in (frankfurter, er_api):
        try:
            rates, date, src = fn(ccys)
            json.dump({"status": "LIVE", "source": src, "rate_date": date, "fetched_at": common.now().isoformat(timespec="seconds"), "rates": rates}, open(WORK / "rates.json", "w"), indent=2)
            log(f"LIVE rates obtained from {src}, dated {date}: " + ", ".join(f"{k}={v:.4f}" for k, v in rates.items()))
            return 0
        except Exception as e:
            log(f"{fn.__name__} failed: {type(e).__name__}: {e}", "WARN")
    if a.allow_fallback:
        fb = json.load(open(ROOT / "input" / "rates-fallback.json"))
        json.dump({"status": "FALLBACK", "source": "input/rates-fallback.json (sample rates, NOT LIVE)", "rate_date": fb["as_of"], "fetched_at": common.now().isoformat(timespec="seconds"), "rates": {c: fb["rates"][c] for c in ccys}}, open(WORK / "rates.json", "w"), indent=2)
        log("ALL LIVE SOURCES FAILED. Using FALLBACK sample rates. The report and email must say these are not live.", "ERROR")
        return 2
    log("All live sources failed and fallback not allowed.", "ERROR")
    return 1

if __name__ == "__main__":
    sys.exit(main())
