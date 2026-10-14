"""Shared helpers: worklog, formatting, paths. Used by every script."""
import datetime, pathlib
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
WORK = ROOT / "output" / "work"


def now():
    return datetime.datetime.now(ZoneInfo("Asia/Kolkata"))


def start_worklog():
    """Create worklog/DDMMYYYYHHMMSS-worklog.md and remember it as the current worklog."""
    (ROOT / "worklog").mkdir(exist_ok=True)
    ts = now().strftime("%d%m%Y%H%M%S")
    f = ROOT / "worklog" / f"{ts}-worklog.md"
    f.write_text(
        "# Worklog: forex exposure agent\n\n"
        f"Run started: {now().strftime('%d-%m-%Y %H:%M:%S')} IST\n\n"
        "| Time (IST) | Level | Activity |\n|---|---|---|\n",
        encoding="utf-8",
    )
    (ROOT / "worklog" / ".current").write_text(str(f), encoding="utf-8")
    return f


def current_worklog():
    p = ROOT / "worklog" / ".current"
    return pathlib.Path(p.read_text().strip()) if p.exists() else None


def log(msg, level="INFO"):
    """Append one timestamped row to the current worklog and echo it to the console."""
    msg = str(msg).replace("|", "/").replace("\n", " ")
    line = f"| {now().strftime('%H:%M:%S')} | {level} | {msg} |"
    f = current_worklog()
    if f and f.exists():
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(f"[{level}] {msg}")


def group_indian(x, dec=0):
    neg = x < 0
    s = f"{abs(x):.{dec}f}"
    ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail, parts = ip[:-3], ip[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ",".join(parts + [tail])
    return ("-" if neg else "") + ip + ("." + fp if dec else "")


def rs(x, dec=0):
    return "Rs " + group_indian(x, dec)


def cr(x, dec=2):
    """Rupees to crore text, e.g. Rs 12.34 Cr."""
    v = x / 1e7
    return ("-" if v < 0 else "") + "Rs " + group_indian(abs(v), dec) + " Cr"


def signed_cr(x, dec=2):
    v = x / 1e7
    return ("+" if v >= 0 else "-") + "Rs " + group_indian(abs(v), dec) + " Cr"
