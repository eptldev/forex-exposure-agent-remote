"""Render template/template.md into a fixed-format, self-contained HTML note.

Usage: python3 scripts/render_report.py [--commentary output/work/commentary.md]
Inputs: template/template.md, output/work/exposure.json, output/work/commentary.md
Output: output/DDMMYYYYHHMMSS-forex-exposure-note.html

Template syntax: '# ' title, line after it is the subtitle, '## ' section heading, '- ' bullet,
{{key}} metric, {{TABLE:name}}, {{COMMENTARY:name}} (headline, drivers, actions).
Plain HTML text only, by design: no embedded images or binary data, so the file can be
uploaded to Google Drive as exact text with no transcription risk.
"""
import argparse, json, re
import common
from common import log, ROOT, WORK

STYLE = """
body{font-family:Helvetica,Arial,sans-serif;color:#1F2A1E;max-width:900px;margin:24px auto;padding:0 16px;line-height:1.5}
header{background:#4F6F48;color:#fff;padding:10px 16px;font-size:12px;font-weight:bold;letter-spacing:.02em;margin:-16px -16px 20px -16px}
h1{font-size:22px;margin:4px 0 2px 0;color:#1F2A1E}
.sub{color:#4A5648;font-size:11px;margin-bottom:6px}
.rule{height:2px;background:#7BA874;border:0;margin:8px 0 18px 0}
h2{font-size:14px;color:#4F6F48;border-bottom:1px solid #D5DDD2;padding-bottom:3px;margin-top:22px}
p{font-size:11px;margin:4px 0}
ul{margin:4px 0;padding-left:18px}
li{font-size:11px;margin:2px 0}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:10.5px}
th{background:#4F6F48;color:#fff;text-align:left;padding:4px 6px}
td{padding:4px 6px;border-bottom:1px solid #D5DDD2}
tr:nth-child(even) td{background:#EEF3EC}
.r{text-align:right}
footer{color:#4A5648;font-size:9px;margin-top:28px;border-top:1px solid #D5DDD2;padding-top:6px}
"""

def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def commentary_sections(path):
    txt = open(path, encoding="utf-8").read()
    secs = {}
    for m in re.finditer(r"^##\s*(\w+)\s*\n(.*?)(?=^##\s|\Z)", txt, re.S | re.M):
        secs[m.group(1).lower()] = m.group(2).strip()
    for k in ("headline", "drivers", "actions"):
        if not secs.get(k): raise SystemExit(f"commentary.md is missing section '## {k}'")
    return secs

def block_html(text):
    out, in_ul = [], False
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln: continue
        if ln.startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{esc(ln[2:])}</li>")
        else:
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<p>{esc(ln)}</p>")
    if in_ul: out.append("</ul>")
    return "\n".join(out)

def table_html(spec):
    head, rows, al = spec["head"], spec["rows"], spec["align"]
    th = "".join(f"<th class='{'r' if a == 'R' else ''}'>{esc(h)}</th>" for h, a in zip(head, al))
    body = []
    for r in rows:
        tds = "".join(f"<td class='{'r' if a == 'R' else ''}'>{esc(c)}</td>" for c, a in zip(r, al))
        body.append(f"<tr>{tds}</tr>")
    return f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--commentary", default=str(WORK / "commentary.md"))
    a = ap.parse_args()
    ex = json.load(open(WORK / "exposure.json")); M, T = ex["metrics"], ex["tables"]
    sec = commentary_sections(a.commentary)
    lines = open(ROOT / "template" / "template.md", encoding="utf-8").read().splitlines()
    unresolved = set()
    def sub(t):
        def r(m):
            k = m.group(1)
            if k in M: return str(M[k])
            unresolved.add(k); return m.group(0)
        return re.sub(r"\{\{(\w+)\}\}", r, t)

    body, i = [], 0
    while i < len(lines):
        ln = lines[i].rstrip(); i += 1
        if not ln.strip(): continue
        if ln.startswith("# "):
            body.append(f"<h1>{esc(sub(ln[2:]))}</h1>")
            if i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "{{", "-")):
                body.append(f"<div class='sub'>{esc(sub(lines[i]))}</div>"); i += 1
            body.append("<hr class='rule'>"); continue
        if ln.startswith("## "):
            body.append(f"<h2>{esc(sub(ln[3:]))}</h2>"); continue
        m = re.fullmatch(r"\{\{(TABLE|COMMENTARY):(\w+)\}\}", ln.strip())
        if m:
            kind, name = m.groups()
            if kind == "TABLE":
                if name not in T: unresolved.add("TABLE:" + name); continue
                body.append(table_html(T[name]))
            else:
                if name not in sec: unresolved.add("COMMENTARY:" + name); continue
                body.append(block_html(sub(sec[name])))
        elif ln.startswith("- "):
            item = f"<li>{esc(sub(ln[2:]))}</li>"
            if body and body[-1].startswith("<ul>") and body[-1].endswith("</ul>"):
                body[-1] = body[-1][:-5] + item + "</ul>"
            else:
                body.append(f"<ul>{item}</ul>")
        else:
            body.append(f"<p>{esc(sub(ln))}</p>")
    if unresolved:
        log(f"Template has unresolved placeholders: {sorted(unresolved)}", "ERROR"); raise SystemExit(1)

    html = (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<title>Forex Exposure Note</title>"
        f"<style>{STYLE}</style></head><body>"
        "<header>BSNL CORPORATE OFFICE &nbsp;|&nbsp; FINANCE AND ACCOUNTS &nbsp;|&nbsp; CFO NOTE</header>"
        + "\n".join(body) +
        "<footer>Prepared by an AI agent (Ayutech AI Labs demo). Training sample data. Verify before use.</footer>"
        "</body></html>"
    )
    out = ROOT / "output" / f"{common.now().strftime('%d%m%Y%H%M%S')}-forex-exposure-note.html"
    out.write_text(html, encoding="utf-8")
    log(f"HTML report written: {out.name} ({out.stat().st_size} bytes)")
    print(out)

if __name__ == "__main__":
    main()
