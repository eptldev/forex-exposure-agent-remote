# Forex exposure agent (demo)

An agent that reads a sheet of foreign-currency vendor payments, fetches live exchange rates from the internet, works out the exposure, writes a fixed-format PDF note for the CFO, saves it to the output folder and emails the CFO.

## Folder structure
- input/      foreign-currency-payments-due.xlsx (50 sample rows, 3 deliberate data errors), rates-fallback.json
- worklog/    one DDMMYYYYHHMMSS-worklog.md per run
- template/   template.md, the fixed layout of the CFO note
- workflow/   workflow.md, all instructions for the agent
- scripts/    start_run.py, fetch_rates.py, write_rates.py, compute_exposure.py, render_report.py, common.py, mock_rates.py (testing only)
- output/     the finished PDF and Excel workbook (and output/work for intermediates)

## Before the demo
1. Python 3 with pandas, openpyxl, matplotlib and reportlab (pip install pandas openpyxl matplotlib reportlab).
2. The agent needs internet access (for the rate fetch) and your Gmail connector, signed in as the sender.
3. Delete old worklog files and old files in output/ so the audience sees a clean run.
4. If the shell cannot reach the internet, the agent switches to its web fetch tool for the rates and saves them with scripts/write_rates.py. This is normal and is logged as an information row.
5. In the app's permission settings, set the Gmail send action to always allow, so the email is not blocked.

## Start the agent
Open this folder in Claude Cowork and send:

Read claude.md and workflow/workflow.md, then run the workflow. The email to the CFO must be sent, not drafted.

## What the audience will see
1. A worklog file appears and fills up as the agent works.
2. The agent calls out to the public rate APIs.
3. It reads the sheet, flags the 3 bad rows and calculates the exposure.
4. It writes the commentary and builds the PDF from the template.
5. The PDF and workbook appear in output/.
6. A short notification email (no figures, no attachment) is sent to director@ayutechservices.com.

## Things to know
- The data is fictional. Vendor names are invented.
- Rates are ECB reference rates (via Frankfurter) or a second public source, not RBI rates. The note says so.
- If every live source fails, the agent uses sample fallback rates and states this in both the PDF and the email.
- Ways to extend the demo live: edit workflow.md (for example ask for a hedge recommendation) or template.md, then run again.
