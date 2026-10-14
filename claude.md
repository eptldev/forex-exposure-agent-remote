# Forex exposure agent

This folder is a self-contained agent. Your task is described in `workflow/workflow.md`. Read it fully before doing anything, then follow it step by step.

Folders:
- `input/` the sheet of foreign-currency vendor payments due, and a fallback rate file
- `workflow/` the instructions (`workflow.md`)
- `template/` the CFO report template (`template.md`)
- `scripts/` helpers that do the calculations, the rate fetch and the HTML rendering
- `worklog/` your activity log, one file per run, named DDMMYYYYHHMMSS-worklog.md
- `output/` the HTML note and the HTML workbook; `output/work/` holds intermediate files

Standing rules: never use an em dash; never invent figures; the email to the CFO must be sent, not drafted; record everything in the worklog.
