"""TESTING ONLY: writes output/work/rates.json with made-up rates so the pipeline can be tested offline.
Never use in a real run. The status is set to MOCK so it is obvious in the report."""
import json, common
common.WORK.mkdir(parents=True, exist_ok=True)
json.dump({"status": "MOCK", "source": "mock_rates.py (testing only)", "rate_date": "test", "fetched_at": "", "rates": {"USD": 88.4, "EUR": 103.1, "GBP": 116.2, "JPY": 0.59, "CNY": 12.45, "SGD": 69.2}}, open(common.WORK / "rates.json", "w"), indent=2)
print("mock rates written")
