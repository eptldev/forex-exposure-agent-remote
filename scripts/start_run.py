"""Step 1 of every run: create the worklog file. Prints its path."""
import common
f = common.start_worklog()
common.log("Run started. Worklog created: " + f.name)
print(f)
