"""Write output/work/rates.json from rates the agent fetched itself (for example with web fetch).

Usage: python3 scripts/write_rates.py USD=88.1234 EUR=102.5 --date 2026-10-12 \
         --source "Frankfurter (ECB reference rates) via web fetch"
Values are INR per 1 unit of the foreign currency. Status is always LIVE, so only use this
for rates actually fetched from the internet in this run.
"""
import argparse, json
import common
from common import log, WORK

ap = argparse.ArgumentParser()
ap.add_argument("pairs", nargs="+"); ap.add_argument("--date", required=True); ap.add_argument("--source", required=True)
a = ap.parse_args()
rates = {}
for p in a.pairs:
    k, v = p.split("=")
    rates[k.strip().upper()] = float(v)
WORK.mkdir(parents=True, exist_ok=True)
json.dump({"status": "LIVE", "source": a.source, "rate_date": a.date, "fetched_at": common.now().isoformat(timespec="seconds"), "rates": rates}, open(WORK / "rates.json", "w"), indent=2)
log(f"Rates written from agent-fetched data ({a.source}, dated {a.date}): " + ", ".join(f"{k}={v:.4f}" for k, v in rates.items()))
