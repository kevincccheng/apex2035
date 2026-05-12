# core/exports.py — text-based PDF generation via ReportLab
# Text is selectable/copyable for AI ingestion (Claude, Gemini, etc.)
import io
import datetime
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, PageBreak,
)

# ── Palette ────────────────────────────────────────────────────────
_DARK_BLUE  = colors.HexColor("#1F3864")
_MID_BLUE   = colors.HexColor("#2E75B6")
_GREEN_BG   = colors.HexColor("#d4edda")
_YELLOW_BG  = colors.HexColor("#fff3cd")
_RED_BG     = colors.HexColor("#f8d7da")
_LIGHT_GREY = colors.HexColor("#F2F4F7")
_BORDER     = colors.HexColor("#CCCCCC")
_GREEN_TXT  = colors.HexColor("#1a5c2a")
_AMBER_TXT  = colors.HexColor("#856404")
_RED_TXT    = colors.HexColor("#721c24")

_HKT = datetime.timezone(datetime.timedelta(hours=8))


def _now_str():
    return datetime.datetime.now(_HKT).strftime("%Y-%m-%d %H:%M HKT")


def _styles():
    ss = getSampleStyleSheet()
    return {
        "title":   ParagraphStyle("t",  parent=ss["Heading1"], fontSize=15,
                                  spaceAfter=4, textColor=_DARK_BLUE),
        "heading": ParagraphStyle("h",  parent=ss["Heading2"], fontSize=11,
                                  spaceAfter=3, textColor=_DARK_BLUE),
        "body":    ParagraphStyle("b",  parent=ss["Normal"],   fontSize=9,
                                  spaceAfter=2),
        "small":   ParagraphStyle("s",  parent=ss["Normal"],   fontSize=8,
                                  textColor=colors.grey, spaceAfter=2),
    }


def _tbl_style(n_rows, header_rows=1, hdr_color=None):
    hdr = hdr_color or _DARK_BLUE
    cmds = [
        ("BACKGROUND",   (0, 0), (-1, header_rows - 1), hdr),
        ("TEXTCOLOR",    (0, 0), (-1, header_rows - 1), colors.white),
        ("FONTNAME",     (0, 0), (-1, header_rows - 1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, header_rows - 1), 9),
        ("FONTSIZE",     (0, header_rows), (-1, -1), 8),
        ("FONTNAME",     (0, header_rows), (-1, -1), "Helvetica"),
        ("ALIGN",        (0, 0), (-1, -1), "LEFT"),
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("GRID",         (0, 0), (-1, -1), 0.3, _BORDER),
        ("TOPPADDING",   (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
        ("LEFTPADDING",  (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]
    for i in range(header_rows, n_rows):
        if i % 2 == 0:
            cmds.append(("BACKGROUND", (0, i), (-1, i), _LIGHT_GREY))
    return TableStyle(cmds)


def _fmt_num(v, prefix="$", suffix="", decimals=0):
    if v is None or (isinstance(v, float) and (v != v)):  # NaN
        return "—"
    try:
        fmt = f"{prefix}{float(v):,.{decimals}f}{suffix}"
        return fmt
    except Exception:
        return str(v)


def _fmt_bn(v):
    if v is None:
        return "N/A"
    try:
        v = float(v)
        if abs(v) >= 1e12: return f"${v/1e12:.2f}T"
        if abs(v) >= 1e9:  return f"${v/1e9:.2f}B"
        if abs(v) >= 1e6:  return f"${v/1e6:.0f}M"
        return f"${v:,.0f}"
    except Exception:
        return "N/A"


# ══════════════════════════════════════════════════════════════════
# PORTFOLIO PDF
# ══════════════════════════════════════════════════════════════════
def export_portfolio_pdf(port_df: pd.DataFrame,
                          summary: dict,
                          fx_rate: float,
                          report_ccy: str,
                          conc_df: pd.DataFrame = None,
                          comp_df: pd.DataFrame = None) -> bytes:
    """
    Generates a 4-page portfolio PDF with selectable text.
    Pages: Executive Summary | Allocation Tables | Full Holdings | Alerts
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch,
    )
    st = _styles()
    story = []
    sym = "HK$" if report_ccy == "HKD" else "$"

    total_mv   = summary.get("total_mv",   0) or 0
    total_cost = summary.get("total_cost", 0) or 0
    total_gl   = summary.get("total_gl",   0) or 0
    gl_pct     = summary.get("total_gl_pct", 0) or 0
    pct_to_5x  = summary.get("pct_to_5x",  0) or 0
    n_pos      = summary.get("n_positions", 0)

    # ── PAGE 1: Executive Summary ─────────────────────────────────
    story.append(Paragraph("Apex 2035 — Portfolio Report", st["title"]))
    story.append(Paragraph(
        f"Generated: {_now_str()}  |  Currency: {report_ccy}  |  "
        f"FX USD/HKD: {fx_rate:.4f}", st["small"]))
    story.append(Spacer(1, 0.12*inch))

    sum_data = [
        ["Metric", "Value"],
        ["Total Market Value",   f"{sym}{total_mv:,.0f}"],
        ["Total Cost Basis",     f"{sym}{total_cost:,.0f}"],
        ["Unrealized G/L",       f"{sym}{total_gl:+,.0f}"],
        ["G/L %",                f"{gl_pct:+.2f}%"],
        ["Positions",            str(n_pos)],
        ["5x Target",            f"{sym}{summary.get('target_5x', 13350000):,.0f}"],
        ["Progress to 5x",       f"{pct_to_5x:.1f}%"],
    ]
    t = Table(sum_data, colWidths=[2.5*inch, 2.2*inch])
    t.setStyle(_tbl_style(len(sum_data)))
    story.append(Paragraph("Portfolio Summary", st["heading"]))
    story.append(t)
    story.append(Spacer(1, 0.15*inch))

    # Top 5 positions
    story.append(Paragraph("Top 5 Positions by Market Value", st["heading"]))
    _mv_col = pd.to_numeric(port_df["mv_usd"], errors="coerce")
    top5 = port_df.assign(_mv_sort=_mv_col).dropna(subset=["_mv_sort"]).nlargest(5, "_mv_sort")
    total_usd = port_df["mv_usd"].sum() or 1
    top5_data = [["Ticker", "Name", "MV (USD)", "% Port", "G/L %"]]
    for _, r in top5.iterrows():
        mv = r.get("mv_usd") or 0
        gp = r.get("gl_pct")
        top5_data.append([
            r["ticker"],
            str(r["name"] or "")[:28],
            f"${mv:,.0f}",
            f"{mv/total_usd*100:.1f}%",
            f"{gp:+.1f}%" if (gp is not None and str(gp) != "nan") else "—",
        ])
    t5 = Table(top5_data, colWidths=[0.8*inch, 2.5*inch, 1.1*inch, 0.8*inch, 0.8*inch])
    t5.setStyle(_tbl_style(len(top5_data)))
    story.append(t5)
    story.append(Spacer(1, 0.15*inch))

    # Alerts summary
    story.append(Paragraph("Alerts Summary", st["heading"]))
    n_conc = len(conc_df) if conc_df is not None else 0
    n_comp = len(comp_df) if comp_df is not None else 0
    n_np   = int(port_df["live_price"].isna().sum())
    al_data = [
        ["Alert Type", "Count"],
        ["Concentration > 5% of portfolio", str(n_conc)],
        ["Compliance flags",                str(n_comp)],
        ["Positions missing live price",    str(n_np)],
    ]
    ta = Table(al_data, colWidths=[3.2*inch, 1.0*inch])
    ta.setStyle(_tbl_style(len(al_data)))
    story.append(ta)

    story.append(PageBreak())

    # ── PAGE 2: Allocation Tables ─────────────────────────────────
    story.append(Paragraph("Portfolio Allocation Breakdown", st["title"]))
    story.append(Paragraph(f"As of {_now_str()}", st["small"]))
    story.append(Spacer(1, 0.1*inch))

    valid = port_df[port_df["mv_usd"].notna()].copy()
    total_mv_usd = valid["mv_usd"].sum() or 1

    for group_col, label in [("barbell_class", "By Barbell Class"),
                               ("region",        "By Region"),
                               ("sector",        "By Sector")]:
        story.append(Paragraph(label, st["heading"]))
        grouped = (valid.groupby(group_col)["mv_usd"].sum()
                        .reset_index()
                        .sort_values("mv_usd", ascending=False))
        rows = [["Group", "MV (USD)", "% Portfolio"]]
        for _, r in grouped.iterrows():
            rows.append([
                r[group_col],
                f"${r['mv_usd']:,.0f}",
                f"{r['mv_usd']/total_mv_usd*100:.1f}%",
            ])
        rows.append(["TOTAL", f"${total_mv_usd:,.0f}", "100.0%"])
        tbl = Table(rows, colWidths=[2.8*inch, 1.8*inch, 1.4*inch])
        s = _tbl_style(len(rows))
        s.add("FONTNAME", (0, len(rows)-1), (-1, len(rows)-1), "Helvetica-Bold")
        tbl.setStyle(s)
        story.append(tbl)
        story.append(Spacer(1, 0.15*inch))

    story.append(PageBreak())

    # ── PAGE 3: Full Holdings ─────────────────────────────────────
    story.append(Paragraph("Full Holdings", st["title"]))
    story.append(Paragraph(
        f"All positions sorted by market value descending. {_now_str()}.",
        st["small"]))
    story.append(Spacer(1, 0.08*inch))

    hdr = ["Ticker", "Name", "Shares", "Price", "MV (USD)", "Cost (USD)", "G/L (USD)", "G/L%"]
    rows = [hdr]
    _sorted_df = port_df.copy()
    _sorted_df["_mv_sort"] = pd.to_numeric(_sorted_df["mv_usd"], errors="coerce")
    _sorted_df = _sorted_df.sort_values("_mv_sort", ascending=False, na_position="last")
    for _, r in _sorted_df.iterrows():
        gp  = r.get("gl_pct")
        gl  = r.get("gl_usd")
        mv  = r.get("mv_usd")
        cst = r.get("cost_usd")
        lp  = r.get("live_price")
        sh  = r.get("shares", 0)
        rows.append([
            r["ticker"],
            str(r["name"] or "")[:22],
            f"{sh:,.2f}" if sh else "—",
            f"{lp:,.2f}" if lp else "—",
            f"${mv:,.0f}"  if (mv  is not None and str(mv)  != "nan") else "—",
            f"${cst:,.0f}" if (cst is not None and str(cst) != "nan") else "—",
            (f"${gl:+,.0f}" if (gl is not None and str(gl) != "nan") else "—"),
            (f"{gp:+.1f}%" if (gp is not None and str(gp) != "nan") else "—"),
        ])
    col_w = [0.65*inch, 1.85*inch, 0.65*inch, 0.65*inch,
             0.85*inch, 0.85*inch, 0.85*inch, 0.60*inch]
    tbl = Table(rows, colWidths=col_w, repeatRows=1)
    tbl.setStyle(_tbl_style(len(rows)))
    story.append(tbl)

    story.append(PageBreak())

    # ── PAGE 4: Alerts ────────────────────────────────────────────
    story.append(Paragraph("Alerts & Compliance", st["title"]))
    story.append(Spacer(1, 0.08*inch))

    story.append(Paragraph("Concentration Alerts (> 5% of portfolio)", st["heading"]))
    if conc_df is not None and not conc_df.empty:
        cd = [["Ticker", "Name", "MV (USD)", "% Portfolio"]]
        for _, r in conc_df.iterrows():
            cd.append([
                r.get("ticker", ""),
                str(r.get("name", "") or "")[:28],
                f"${r.get('mv_usd', 0):,.0f}",
                f"{r.get('pct_of_port', 0):.1f}%",
            ])
        tc = Table(cd, colWidths=[0.8*inch, 2.5*inch, 1.2*inch, 1.0*inch])
        tc.setStyle(_tbl_style(len(cd)))
        story.append(tc)
    else:
        story.append(Paragraph("No concentration alerts.", st["body"]))
    story.append(Spacer(1, 0.12*inch))

    story.append(Paragraph("Compliance Issues", st["heading"]))
    if comp_df is not None and not comp_df.empty:
        cd2 = [["Ticker", "Name", "Sector", "Flag"]]
        for _, r in comp_df.iterrows():
            cd2.append([
                r.get("ticker", ""),
                str(r.get("name", "") or "")[:22],
                str(r.get("sector", "") or "")[:20],
                r.get("flags", ""),
            ])
        tc2 = Table(cd2, colWidths=[0.8*inch, 2.0*inch, 1.5*inch, 2.0*inch])
        tc2.setStyle(_tbl_style(len(cd2)))
        story.append(tc2)
    else:
        story.append(Paragraph("No compliance violations.", st["body"]))
    story.append(Spacer(1, 0.12*inch))

    story.append(Paragraph("Positions Missing Live Price", st["heading"]))
    no_price = port_df[port_df["live_price"].isna()][
        ["ticker", "name", "sector", "price_error"]]
    if not no_price.empty:
        np_d = [["Ticker", "Name", "Sector", "Error"]]
        for _, r in no_price.iterrows():
            np_d.append([
                r.get("ticker", ""),
                str(r.get("name", "") or "")[:22],
                str(r.get("sector", "") or "")[:18],
                str(r.get("price_error", "") or "")[:28],
            ])
        tnp = Table(np_d, colWidths=[0.8*inch, 2.0*inch, 1.5*inch, 2.0*inch])
        tnp.setStyle(_tbl_style(len(np_d)))
        story.append(tnp)
    else:
        story.append(Paragraph("All positions have live prices.", st["body"]))

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# STOCK ANALYZER PDF
# ══════════════════════════════════════════════════════════════════
def export_stock_pdf(ticker: str, result: dict, fair_value: dict = None) -> bytes:
    """
    Generates a stock analysis PDF (3 pages + optional fair value page).
    Pages: Company Overview + Verdict | 10-Pillar Scorecard |
           Historical Data | Fair Value (if provided)
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch,
    )
    st = _styles()
    story = []

    info      = result.get("company_info", {})
    pillars   = result.get("pillars", [])
    score     = result.get("score", 0)
    verdict   = result.get("verdict", "N/A")
    hist      = result.get("historical", [])

    # ── PAGE 1: Company Overview ──────────────────────────────────
    story.append(Paragraph(f"Stock Analysis: {ticker}", st["title"]))
    story.append(Paragraph(f"Analysis date: {_now_str()}", st["small"]))
    story.append(Spacer(1, 0.12*inch))

    mc  = info.get("market_cap")
    mc_str = (_fmt_bn(mc).replace("$", "USD ") if mc else "N/A")
    px  = info.get("price")
    ccy = info.get("currency", "USD")
    px_str = f"{ccy} {px:,.2f}" if px else "N/A"
    h52  = info.get("week_52_high")
    l52  = info.get("week_52_low")
    rng  = (f"{l52:,.2f} – {h52:,.2f} {ccy}" if (h52 and l52) else "N/A")

    co_data = [
        ["Field", "Value"],
        ["Company",       info.get("name", ticker)],
        ["Sector",        info.get("sector", "N/A")],
        ["Market Cap",    mc_str],
        ["Current Price", px_str],
        ["52-Week Range", rng],
        ["Currency",      ccy],
    ]
    tc = Table(co_data, colWidths=[2.0*inch, 4.0*inch])
    tc.setStyle(_tbl_style(len(co_data)))
    story.append(Paragraph("Company Overview", st["heading"]))
    story.append(tc)
    story.append(Spacer(1, 0.15*inch))

    # Verdict card
    story.append(Paragraph("Overall Assessment", st["heading"]))
    vdict = {
        "CHEAP":     (_GREEN_BG, _GREEN_TXT),
        "FAIR":      (_YELLOW_BG, _AMBER_TXT),
        "EXPENSIVE": (_RED_BG,   _RED_TXT),
    }
    v_bg, v_tc = vdict.get(verdict, (_LIGHT_GREY, colors.black))
    v_data = [["Overall Score", "Verdict"],
              [f"{score} / 10",  verdict]]
    tv = Table(v_data, colWidths=[2.5*inch, 3.0*inch])
    vs = _tbl_style(2)
    vs.add("BACKGROUND", (0, 1), (-1, 1), v_bg)
    vs.add("TEXTCOLOR",  (0, 1), (-1, 1), v_tc)
    vs.add("FONTNAME",   (0, 1), (-1, 1), "Helvetica-Bold")
    vs.add("FONTSIZE",   (0, 1), (-1, 1), 13)
    tv.setStyle(vs)
    story.append(tv)

    story.append(PageBreak())

    # ── PAGE 2: 10-Pillar Scorecard ───────────────────────────────
    story.append(Paragraph("10-Pillar Scorecard", st["title"]))
    story.append(Paragraph(
        f"Ticker: {ticker}  |  Score: {score}/10  |  Verdict: {verdict}  |  {_now_str()}",
        st["small"]))
    story.append(Spacer(1, 0.08*inch))

    p_data = [["#", "Pillar", "Value", "Rating", "Note"]]
    for p in pillars:
        p_data.append([
            str(p["number"]),
            p["name"],
            p["value"],
            p["rating"],
            p["note"],
        ])

    cw = [0.25*inch, 1.55*inch, 1.55*inch, 0.65*inch, 2.25*inch]
    tp = Table(p_data, colWidths=cw, repeatRows=1)
    ps = _tbl_style(len(p_data))
    rating_map = {
        "GREEN":  (_GREEN_BG,  _GREEN_TXT),
        "YELLOW": (_YELLOW_BG, _AMBER_TXT),
        "RED":    (_RED_BG,    _RED_TXT),
    }
    for i, p in enumerate(pillars, 1):
        if p["rating"] in rating_map:
            bg, tc2 = rating_map[p["rating"]]
            ps.add("BACKGROUND", (3, i), (3, i), bg)
            ps.add("TEXTCOLOR",  (3, i), (3, i), tc2)
            ps.add("FONTNAME",   (3, i), (3, i), "Helvetica-Bold")
    tp.setStyle(ps)
    story.append(tp)

    # ── PAGE 3: Key Historical Data ───────────────────────────────
    if hist:
        story.append(PageBreak())
        story.append(Paragraph("Key Historical Financial Data", st["title"]))
        story.append(Paragraph(
            f"Source: yfinance  |  Values in reporting currency of the company.",
            st["small"]))
        story.append(Spacer(1, 0.08*inch))

        h_data = [["Year", "Revenue", "Net Income", "FCF", "Gross Margin", "Diluted Shares"]]
        for h in hist:
            sh = h.get("shares")
            if sh:
                sh_str = (f"{sh/1e9:.2f}B" if sh >= 1e9
                          else f"{sh/1e6:.0f}M" if sh >= 1e6 else f"{sh:,.0f}")
            else:
                sh_str = "N/A"
            h_data.append([
                str(h.get("year", "N/A")),
                _fmt_bn(h.get("revenue")),
                _fmt_bn(h.get("net_income")),
                _fmt_bn(h.get("fcf")),
                f"{h.get('gross_margin_pct'):.1f}%" if h.get("gross_margin_pct") else "N/A",
                sh_str,
            ])
        th = Table(h_data,
                   colWidths=[0.55*inch, 1.05*inch, 1.05*inch, 1.05*inch, 1.05*inch, 1.0*inch])
        th.setStyle(_tbl_style(len(h_data)))
        story.append(th)

    # ── PAGE 4 (optional): Fair Value ────────────────────────────
    if fair_value and "error" not in fair_value:
        story.append(PageBreak())
        story.append(Paragraph("Fair Value Analysis", st["title"]))
        story.append(Paragraph(
            "DCF model — Paul Gabrail / Everything Money methodology.",
            st["small"]))
        story.append(Spacer(1, 0.1*inch))

        fv_sym = "HK$" if ticker.endswith(".HK") else "$"
        fv_rows = [
            ["Metric", "Value"],
            ["Current Price",    f"{fv_sym}{fair_value['current_price']:,.2f}"],
            ["Bear Case (−25%)", f"{fv_sym}{fair_value['fair_value_bear']:,.2f}"],
            ["Base Case",        f"{fv_sym}{fair_value['fair_value_base']:,.2f}"],
            ["Bull Case (+25%)", f"{fv_sym}{fair_value['fair_value_bull']:,.2f}"],
            ["Upside vs Current",f"{fair_value['upside_pct']:+.1f}%"],
            ["Margin of Safety", f"{fair_value['margin_of_safety']:+.1f}%"],
            ["Verdict",          fair_value["verdict"]],
        ]
        tfv = Table(fv_rows, colWidths=[2.5*inch, 2.5*inch])
        fvs = _tbl_style(len(fv_rows))
        vdict = {"UNDERVALUED": _GREEN_BG, "FAIRLY VALUED": _YELLOW_BG,
                  "OVERVALUED": _RED_BG}
        vbg = vdict.get(fair_value["verdict"], _LIGHT_GREY)
        fvs.add("BACKGROUND", (0, len(fv_rows)-1), (-1, len(fv_rows)-1), vbg)
        fvs.add("FONTNAME",   (0, len(fv_rows)-1), (-1, len(fv_rows)-1), "Helvetica-Bold")
        tfv.setStyle(fvs)
        story.append(Paragraph("Valuation Summary", st["heading"]))
        story.append(tfv)
        story.append(Spacer(1, 0.15*inch))

        # Assumptions
        a = fair_value.get("assumptions", {})
        if a:
            story.append(Paragraph("Assumptions Used", st["heading"]))
            a_rows = [
                ["Parameter", "Value"],
                ["Revenue Growth / yr",  f"{a.get('revenue_growth_rate', 0):.0f}%"],
                ["Target Profit Margin", f"{a.get('target_profit_margin', 0):.0f}%"],
                ["FCF Margin",           f"{a.get('target_fcf_margin', 0):.0f}%"],
                ["Required Return",      f"{a.get('required_return', 0):.0f}%"],
                ["Terminal P/E",         f"{a.get('terminal_pe', 0):.0f}×"],
                ["Projection Years",     str(a.get("years", 5))],
            ]
            ta = Table(a_rows, colWidths=[2.5*inch, 2.0*inch])
            ta.setStyle(_tbl_style(len(a_rows), hdr_color=_MID_BLUE))
            story.append(ta)

    doc.build(story)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════
# CONVICTION LOG PDF
# ══════════════════════════════════════════════════════════════════
def export_conviction_pdf(conv_df: pd.DataFrame, stats: dict = None) -> bytes:
    """
    Generates a conviction log PDF (3 pages).
    Attach to Claude AI: 'Review my conviction quality.'
    """
    import math

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch,   bottomMargin=0.75*inch,
    )
    st_d = _styles()
    story = []
    stats = stats or {}

    def _safe(v, fallback="—"):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return fallback
        return str(v)

    active = conv_df[conv_df["status"] == "ACTIVE"] \
        if "status" in conv_df.columns else pd.DataFrame()
    closed = conv_df[conv_df["status"] == "CLOSED"] \
        if "status" in conv_df.columns else pd.DataFrame()

    # ── PAGE 1: Active Convictions ────────────────────────────────
    story.append(Paragraph("Conviction Log — Active Positions", st_d["title"]))
    story.append(Paragraph(
        f"Generated: {_now_str()}  |  Active: {len(active)}  |  Closed: {len(closed)}",
        st_d["small"]))
    story.append(Spacer(1, 0.1*inch))

    if active.empty:
        story.append(Paragraph("No active convictions recorded.", st_d["body"]))
    else:
        for _, r in active.iterrows():
            ep  = _safe(r.get("entry_price"))
            hdr = (f"{_safe(r.get('ticker'))} — {_safe(r.get('action'))} @ "
                   f"${ep}  |  {_safe(r.get('entry_date'))}")
            story.append(Paragraph(hdr, st_d["heading"]))
            meta = [
                ["Position Size", f"${_safe(r.get('position_size_usd'))}",
                 "Max Cap", f"${_safe(r.get('max_size_cap_usd'))}"],
                ["Time Horizon", f"{_safe(r.get('time_horizon_months'))} months",
                 "Falsification $", f"${_safe(r.get('falsification_price'))}"],
                ["Opp. Cost", _safe(r.get("opportunity_cost")),
                 "Status", _safe(r.get("status"))],
            ]
            tm = Table(meta, colWidths=[1.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
            tm.setStyle(_tbl_style(len(meta), hdr_color=_MID_BLUE))
            story.append(tm)
            story.append(Spacer(1, 0.04*inch))
            for lbl, fld in [("Thesis", "thesis"),
                              ("Bull Case", "bull_case"),
                              ("Bear Case", "bear_case")]:
                txt = _safe(r.get(fld), "")
                if txt:
                    story.append(Paragraph(f"<b>{lbl}:</b> {txt}", st_d["body"]))
            story.append(Spacer(1, 0.15*inch))

    # ── PAGE 2: Closed Convictions ────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Conviction Log — Closed Positions", st_d["title"]))
    story.append(Spacer(1, 0.08*inch))
    if closed.empty:
        story.append(Paragraph("No closed convictions yet.", st_d["body"]))
    else:
        cl_d = [["Ticker", "Action", "Entry $", "Entry Date",
                  "Review Date", "Grade", "Outcome"]]
        for _, r in closed.iterrows():
            cl_d.append([
                _safe(r.get("ticker")),
                _safe(r.get("action")),
                f"${_safe(r.get('entry_price'))}",
                _safe(r.get("entry_date")),
                _safe(r.get("review_date")),
                _safe(r.get("grade")),
                _safe(r.get("outcome_notes"), "")[:50],
            ])
        tc = Table(cl_d,
                   colWidths=[0.7*inch, 0.9*inch, 0.7*inch, 0.85*inch,
                               0.85*inch, 0.5*inch, 2.25*inch],
                   repeatRows=1)
        tc.setStyle(_tbl_style(len(cl_d)))
        story.append(tc)

    # ── PAGE 3: Track Record ──────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Track Record & Statistics", st_d["title"]))
    story.append(Spacer(1, 0.08*inch))
    s_rows = [
        ["Metric", "Value"],
        ["Total decisions recorded", str(stats.get("total_decisions", len(conv_df)))],
        ["Win rate (A+B grades)",     f"{stats.get('win_rate_pct', 0):.0f}%"],
        ["Average hold period",       f"{stats.get('avg_hold_days', 0):.0f} days"],
        ["Avg P&L closed positions",  f"{stats.get('avg_pnl_pct', 0):+.1f}%"],
        ["Active convictions",        str(len(active))],
        ["Closed convictions",        str(len(closed))],
    ]
    ts = Table(s_rows, colWidths=[3.0*inch, 2.0*inch])
    ts.setStyle(_tbl_style(len(s_rows)))
    story.append(ts)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "Tip: Attach this PDF to Claude AI and ask: "
        "'Review my conviction quality. What patterns do you see in my mistakes?'",
        st_d["small"]))

    doc.build(story)
    return buf.getvalue()
