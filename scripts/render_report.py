"""Render template/template.md into a fixed-format A4 PDF.

Usage: python3 scripts/render_report.py [--commentary output/work/commentary.md]
Inputs: template/template.md, output/work/exposure.json, output/work/commentary.md
Output: output/DDMMYYYYHHMMSS-forex-exposure-note.pdf
Template syntax: '# ' title, line after it is the subtitle, '## ' section heading, '- ' bullet,
{{key}} metric, {{TABLE:name}}, {{CHART:name}}, {{COMMENTARY:name}} (headline, drivers, actions).
"""
import argparse, json, re, sys
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
import common
from common import log, ROOT, WORK

GREEN, ACCENT, TINT, GREY, RUST = "#4F6F48", "#7BA874", "#EEF3EC", "#4A5648", "#B5532F"
S = {
    "title": ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=colors.HexColor("#1F2A1E")),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=10.5, leading=14, textColor=colors.HexColor(GREY), spaceAfter=6),
    "h": ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor(GREEN), spaceBefore=12, spaceAfter=5),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=10, leading=14, textColor=colors.HexColor("#1F2A1E"), spaceAfter=4),
    "b": ParagraphStyle("b", fontName="Helvetica", fontSize=10, leading=14, leftIndent=12, bulletIndent=2, textColor=colors.HexColor("#1F2A1E"), spaceAfter=2),
    "c": ParagraphStyle("c", fontName="Helvetica", fontSize=8, leading=10),
    "ch": ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white),
}

def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def commentary_sections(path):
    txt = open(path, encoding="utf-8").read()
    secs = {}
    for m in re.finditer(r"^##\s*(\w+)\s*\n(.*?)(?=^##\s|\Z)", txt, re.S | re.M):
        secs[m.group(1).lower()] = m.group(2).strip()
    for k in ("headline", "drivers", "actions"):
        if not secs.get(k): raise SystemExit(f"commentary.md is missing section '## {k}'")
    return secs

def block(text):
    out = []
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln: continue
        if ln.startswith("- "): out.append(Paragraph(esc(ln[2:]), S["b"], bulletText="•"))
        else: out.append(Paragraph(esc(ln), S["p"]))
    return out

def table(spec, width):
    head, rows, al = spec["head"], spec["rows"], spec["align"]
    n = len(head)
    data = [[Paragraph(esc(h), S["ch"]) for h in head]]
    for r in rows:
        data.append([Paragraph(esc(c), ParagraphStyle("x", parent=S["c"], alignment=2 if al[i] == "R" else 0)) for i, c in enumerate(r)])
    weights = [min(26, max(len(head[i]) + 2, max((len(r[i]) + 4 for r in rows), default=8), 10)) for i in range(n)]
    cw = [width * w / sum(weights) for w in weights]
    t = Table(data, colWidths=cw, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(GREEN)), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor(TINT)]), ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#D5DDD2")),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if spec.get("boldlast"): st.append(("LINEABOVE", (0, -1), (-1, -1), 0.8, colors.HexColor(GREEN)))
    t.setStyle(TableStyle(st))
    return t

def chart(name, data):
    WORK.mkdir(parents=True, exist_ok=True)
    f = WORK / f"chart-{name}.png"
    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    if name == "delta_by_currency":
        ks = list(data); vs = [data[k] for k in ks]
        ax.bar(ks, vs, color=[RUST if v >= 0 else GREEN for v in vs])
        ax.set_ylabel("Rs crore"); ax.set_title("Additional cost (+) or saving (-) against booked rates, by currency", fontsize=9, loc="left")
        for i, v in enumerate(vs): ax.annotate(f"{v:+.2f}", (i, v), ha="center", va="bottom" if v >= 0 else "top", fontsize=7)
    else:
        ks = list(data); op = [data[k][0] for k in ks]; hd = [data[k][1] for k in ks]
        ax.bar(ks, op, color=GREEN, label="Open (unhedged)"); ax.bar(ks, hd, bottom=op, color=ACCENT, label="Hedged")
        ax.set_ylabel("Rs crore"); ax.set_title("Payment value at live rates by due bucket", fontsize=9, loc="left"); ax.legend(fontsize=7, frameon=False)
    ax.axhline(0, color="#999", lw=0.6)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=7); plt.tight_layout(); fig.savefig(f); plt.close(fig)
    return f

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--commentary", default=str(WORK / "commentary.md"))
    a = ap.parse_args()
    ex = json.load(open(WORK / "exposure.json")); M, T, C = ex["metrics"], ex["tables"], ex["charts"]
    sec = commentary_sections(a.commentary)
    lines = open(ROOT / "template" / "template.md", encoding="utf-8").read().splitlines()
    unresolved = set()
    def sub(t):
        def r(m):
            k = m.group(1)
            if k in M: return M[k]
            unresolved.add(k); return m.group(0)
        return re.sub(r"\{\{(\w+)\}\}", r, t)
    W = A4[0] - 36 * mm
    story, i = [], 0
    pending_head = None
    while i < len(lines):
        ln = lines[i].rstrip(); i += 1
        if not ln.strip(): continue
        if ln.startswith("# "):
            story.append(Paragraph(esc(sub(ln[2:])), S["title"]))
            if i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "{{", "-")):
                story.append(Paragraph(esc(sub(lines[i])), S["sub"])); i += 1
            story.append(Table([[""]], colWidths=[W], rowHeights=[2], style=[("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(ACCENT))])); continue
        if ln.startswith("## "):
            pending_head = Paragraph(esc(sub(ln[3:])), S["h"]); continue
        m = re.fullmatch(r"\{\{(TABLE|CHART|COMMENTARY):(\w+)\}\}", ln.strip())
        items = []
        if m:
            kind, name = m.groups()
            if kind == "TABLE":
                if name not in T: unresolved.add("TABLE:" + name); continue
                items = [table(T[name], W), Spacer(1, 6)]
            elif kind == "CHART":
                if name not in C: unresolved.add("CHART:" + name); continue
                items = [Image(str(chart(name, C[name])), width=W, height=W * 2.6 / 7.2), Spacer(1, 4)]
            else:
                if name not in sec: unresolved.add("COMMENTARY:" + name); continue
                items = block(sub(sec[name]))
        elif ln.startswith("- "): items = [Paragraph(esc(sub(ln[2:])), S["b"], bulletText="•")]
        else: items = [Paragraph(esc(sub(ln)), S["p"])]
        if pending_head is not None:
            story.append(KeepTogether([pending_head] + items[:1])); story.extend(items[1:]); pending_head = None
        else: story.extend(items)
    if unresolved:
        log(f"Template has unresolved placeholders: {sorted(unresolved)}", "ERROR"); raise SystemExit(1)
    out = ROOT / "output" / f"{common.now().strftime('%d%m%Y%H%M%S')}-forex-exposure-note.pdf"
    def deco(c, d):
        c.saveState(); c.setFillColor(colors.HexColor(GREEN)); c.rect(0, A4[1] - 12 * mm, A4[0], 12 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 8.5); c.drawString(18 * mm, A4[1] - 7.5 * mm, "BSNL CORPORATE OFFICE  |  FINANCE AND ACCOUNTS  |  CFO NOTE")
        c.setFillColor(colors.HexColor(GREY)); c.setFont("Helvetica", 7.5)
        c.drawString(18 * mm, 9 * mm, "Prepared by an AI agent (Ayutech AI Labs demo). Training sample data. Verify before use.")
        c.drawRightString(A4[0] - 18 * mm, 9 * mm, f"Page {d.page}"); c.restoreState()
    doc = BaseDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=16 * mm,
                          title="Forex Exposure Note", author="Ayutech AI Labs")
    doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(doc.leftMargin, doc.bottomMargin, W, A4[1] - doc.topMargin - doc.bottomMargin, id="f")], onPage=deco)])
    doc.build(story)
    log(f"PDF written: {out.name}")
    print(out)

if __name__ == "__main__":
    main()
