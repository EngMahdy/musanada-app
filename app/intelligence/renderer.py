"""
PDF + Excel Renderers for Intelligence reports
==============================================
Uses python-docx as a fallback if reportlab isn't available;
keeps dependencies minimal.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

log = logging.getLogger(__name__)


def _try_import_reportlab():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
            PageBreak,
        )
        from reportlab.lib.units import cm, mm
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
        return {
            "A4": A4, "getSampleStyleSheet": getSampleStyleSheet,
            "ParagraphStyle": ParagraphStyle, "SimpleDocTemplate": SimpleDocTemplate,
            "Paragraph": Paragraph, "Spacer": Spacer, "Table": Table,
            "TableStyle": TableStyle, "Image": Image, "PageBreak": PageBreak,
            "cm": cm, "mm": mm, "colors": colors,
            "TA_RIGHT": TA_RIGHT, "TA_CENTER": TA_CENTER, "TA_LEFT": TA_LEFT,
        }
    except ImportError:
        return None


def _reshape_arabic(text: str) -> str:
    """Reshape Arabic for proper PDF rendering."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def render_intelligence_pdfs(
    intel: Dict[str, Any],
    output_dir: Path,
    logo_path: Path | None = None,
) -> Dict[str, Path]:
    """
    Render 5 PDF reports into output_dir. Returns dict of label -> path.
    Falls back to markdown if reportlab missing.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rl = _try_import_reportlab()
    paths: Dict[str, Path] = {}

    if rl is None:
        # Fallback: dump markdown files
        log.warning("reportlab missing — falling back to markdown reports")
        for name, key in [
            ("01_Technical_Brief.md", "technical"),
            ("02_Financial_Analysis.md", "financial"),
            ("03_Market_Report.md", "market"),
            ("04_Strategic_Assessment.md", "strategic"),
            ("05_Executive_Summary_GoNoGo.md", "executive_summary"),
        ]:
            p = output_dir / name
            p.write_text(_fallback_markdown(intel, key), encoding="utf-8")
            paths[key] = p
        return paths

    # ---- reportlab path ----
    paths["technical"] = _render_technical_pdf(intel, output_dir / "01_Technical_Brief.pdf", rl, logo_path)
    paths["financial"] = _render_financial_pdf(intel, output_dir / "02_Financial_Analysis.pdf", rl, logo_path)
    paths["market"] = _render_market_pdf(intel, output_dir / "03_Market_Report.pdf", rl, logo_path)
    paths["strategic"] = _render_strategic_pdf(intel, output_dir / "04_Strategic_Assessment.pdf", rl, logo_path)
    paths["executive_summary"] = _render_summary_pdf(intel, output_dir / "05_Executive_Summary_GoNoGo.pdf", rl, logo_path)

    return paths


# ----------------------------------------------------------------------------
# Common helpers
# ----------------------------------------------------------------------------

def _styles(rl):
    s = rl["getSampleStyleSheet"]()
    s.add(rl["ParagraphStyle"]("ArTitle", parent=s["Title"], fontSize=18, alignment=rl["TA_CENTER"], textColor=rl["colors"].HexColor("#1F3864")))
    s.add(rl["ParagraphStyle"]("ArH1", parent=s["Heading1"], fontSize=14, alignment=rl["TA_RIGHT"], textColor=rl["colors"].HexColor("#1F3864")))
    s.add(rl["ParagraphStyle"]("ArH2", parent=s["Heading2"], fontSize=12, alignment=rl["TA_RIGHT"], textColor=rl["colors"].HexColor("#C49B30")))
    s.add(rl["ParagraphStyle"]("ArNormal", parent=s["Normal"], fontSize=10, alignment=rl["TA_RIGHT"]))
    s.add(rl["ParagraphStyle"]("ArSignal", parent=s["Heading1"], fontSize=42, alignment=rl["TA_CENTER"]))
    return s


def _header(story, rl, logo_path: Path | None, title: str):
    if logo_path and Path(logo_path).exists():
        try:
            img = rl["Image"](str(logo_path), width=4 * rl["cm"], height=4 * rl["cm"])
            img.hAlign = "CENTER"
            story.append(img)
        except Exception:
            pass
    s = _styles(rl)
    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic(title), s["ArTitle"]))
    story.append(rl["Paragraph"](
        _reshape_arabic(f"تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d')}"),
        s["ArNormal"]))
    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))


def _kv_table(rl, rows: list[tuple[str, str]]):
    s = _styles(rl)
    data = [
        [rl["Paragraph"](_reshape_arabic(v), s["ArNormal"]),
         rl["Paragraph"](_reshape_arabic(k), s["ArNormal"])]
        for k, v in rows
    ]
    t = rl["Table"](data, colWidths=[10 * rl["cm"], 7 * rl["cm"]])
    t.setStyle(rl["TableStyle"]([
        ("BOX", (0, 0), (-1, -1), 0.5, rl["colors"].HexColor("#1F3864")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, rl["colors"].HexColor("#888888")),
        ("BACKGROUND", (1, 0), (1, -1), rl["colors"].HexColor("#F2F4F8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ----------------------------------------------------------------------------
# Technical PDF
# ----------------------------------------------------------------------------

def _render_technical_pdf(intel, path, rl, logo_path):
    doc = rl["SimpleDocTemplate"](str(path), pagesize=rl["A4"],
                                  rightMargin=rl["cm"] * 1.5, leftMargin=rl["cm"] * 1.5,
                                  topMargin=rl["cm"] * 1.5, bottomMargin=rl["cm"] * 1.5)
    s = _styles(rl)
    story = []
    _header(story, rl, logo_path, "التحليل الفني للمناقصة")
    req = intel["technical"]["requirements"]
    rows = [
        ("اسم المناقصة", intel["tender_name"]),
        ("المنطقة", intel["area_name"]),
        ("نوع المشروع", intel["project_type"]),
        ("مساحة القطعة", f"{req.get('plot_area') or '—'} م²"),
        ("مدة الإيجار", f"{req.get('lease_term') or '—'} سنة"),
        ("مدة الإنشاء", f"{req.get('construction_period') or '—'}"),
        ("الاستخدام المسموح", req.get('land_use') or '—'),
        ("متطلب ICV", f"{req.get('icv_requirement') or '—'}%"),
        ("ضمان العطاء", f"{req.get('bid_bond') or '—'} AED"),
        ("ضمان الأداء", f"{req.get('performance_bond') or '—'}%"),
    ]
    story.append(_kv_table(rl, rows))
    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))

    story.append(rl["Paragraph"](_reshape_arabic("المتطلبات الخاصة"), s["ArH1"]))
    story.append(rl["Spacer"](1, 0.2 * rl["cm"]))

    flags = [
        ("التوطين (Emiratization)", req.get("requires_emiratization")),
        ("الاستدامة (Estidama/LEED)", req.get("requires_sustainability")),
        ("التشغيل 24/7", req.get("operates_24_7")),
    ]
    for label, val in flags:
        mark = "✅ مطلوب" if val else "➖ غير مطلوب"
        story.append(rl["Paragraph"](_reshape_arabic(f"{mark} — {label}"), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("التوصيات الفنية"), s["ArH1"]))
    recs = [
        "تأكد من توافق التصميم مع الاستخدام المسموح به",
        "خصص في الميزانية بند ICV لو متطلب (10-15% من قيمة العقد)",
        "ضع جدول زمني تفصيلي للإنشاء يتوافق مع المدة المسموحة",
        "تجهيز ضمان العطاء البنكي قبل تاريخ التقديم بأسبوع",
    ]
    for r in recs:
        story.append(rl["Paragraph"](_reshape_arabic(f"• {r}"), s["ArNormal"]))

    doc.build(story)
    return path


# ----------------------------------------------------------------------------
# Financial PDF
# ----------------------------------------------------------------------------

def _render_financial_pdf(intel, path, rl, logo_path):
    doc = rl["SimpleDocTemplate"](str(path), pagesize=rl["A4"],
                                  rightMargin=rl["cm"] * 1.5, leftMargin=rl["cm"] * 1.5,
                                  topMargin=rl["cm"] * 1.5, bottomMargin=rl["cm"] * 1.5)
    s = _styles(rl)
    story = []
    _header(story, rl, logo_path, "التحليل المالي للمناقصة")

    fin = intel["financial"]
    h = fin["headline"]
    a = fin["assumptions"]

    # Assumptions box
    story.append(rl["Paragraph"](_reshape_arabic("الافتراضات الأساسية"), s["ArH1"]))
    story.append(_kv_table(rl, [
        ("مساحة القطعة", f"{a['plot_area_sqm']} م²"),
        ("نوع المشروع", a["project_type"]),
        ("مدة الإيجار", f"{a['lease_years']} سنة"),
        ("سعر الإيجار للمتر/سنة", f"{a['rent_per_sqm_per_year']:,} AED"),
        ("مصدر السعر", a["rent_source"]),
        ("CAPEX للمتر", f"{a['capex_per_sqm']:,} AED"),
        ("نسبة المصاريف من الإيراد", f"{a['opex_rate_of_revenue']*100:.0f}%"),
        ("معدل الخصم (NPV)", f"{a['discount_rate']*100:.0f}%"),
    ]))
    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))

    # Headline metrics
    story.append(rl["Paragraph"](_reshape_arabic("المؤشرات الرئيسية"), s["ArH1"]))
    irr_txt = f"{h['irr_pct']}%" if h.get("irr_pct") is not None else "—"
    payback_txt = f"{h['payback_years']} سنة" if h.get("payback_years") else "—"
    story.append(_kv_table(rl, [
        ("CAPEX (تكلفة البناء)", f"{h['capex']:,.0f} AED"),
        ("الإيراد السنوي (مستقر)", f"{h['annual_revenue_stabilized']:,.0f} AED"),
        ("OPEX السنوي (مستقر)", f"{h['annual_opex_stabilized']:,.0f} AED"),
        ("EBITDA السنوي (مستقر)", f"{h['annual_ebitda_stabilized']:,.0f} AED"),
        ("معدل العائد الداخلي (IRR)", irr_txt),
        ("صافي القيمة الحالية (NPV @ 10%)", f"{h['npv_aed']:,.0f} AED"),
        ("فترة الاسترداد", payback_txt),
        ("صافي الربح طوال الإيجار", f"{h['total_net_profit_lease']:,.0f} AED"),
    ]))
    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))

    # Verdict
    v = fin.get("verdict", {})
    story.append(rl["Paragraph"](_reshape_arabic("التقييم المالي السريع"), s["ArH1"]))
    story.append(rl["Paragraph"](
        _reshape_arabic(f"{v.get('signal', '🟡')}  {v.get('label', '')}"),
        s["ArH2"]))

    story.append(rl["PageBreak"]())

    # Yearly table
    story.append(rl["Paragraph"](_reshape_arabic(f"الجدول السنوي ({a['lease_years']} سنة)"), s["ArH1"]))
    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))

    header = [_reshape_arabic(x) for x in
              ["صافي التدفق", "ضريبة", "EBITDA", "OPEX", "إيراد", "إشغال %", "السنة"]]
    data = [header]
    for r in fin["yearly_table"]:
        data.append([
            f"{r['net_cash_flow']:,.0f}",
            f"{r['tax']:,.0f}",
            f"{r['ebitda']:,.0f}",
            f"{r['opex']:,.0f}",
            f"{r['revenue']:,.0f}",
            f"{r['occupancy_pct']}%",
            str(r["year"]),
        ])
    t = rl["Table"](data, repeatRows=1)
    t.setStyle(rl["TableStyle"]([
        ("GRID", (0, 0), (-1, -1), 0.25, rl["colors"].grey),
        ("BACKGROUND", (0, 0), (-1, 0), rl["colors"].HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), rl["colors"].white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(t)

    doc.build(story)
    return path


# ----------------------------------------------------------------------------
# Market / Strategic / Executive PDFs (shorter, similar pattern)
# ----------------------------------------------------------------------------

def _render_market_pdf(intel, path, rl, logo_path):
    doc = rl["SimpleDocTemplate"](str(path), pagesize=rl["A4"],
                                  rightMargin=rl["cm"] * 1.5, leftMargin=rl["cm"] * 1.5,
                                  topMargin=rl["cm"] * 1.5, bottomMargin=rl["cm"] * 1.5)
    s = _styles(rl)
    story = []
    _header(story, rl, logo_path, "تقرير بحث السوق")

    m = intel["market"]
    c = intel["competition"]

    story.append(rl["Paragraph"](_reshape_arabic("متوسط الإيجارات المُكتشفة"), s["ArH1"]))
    avg = m.get("avg_rent_per_sqm_per_year")
    story.append(_kv_table(rl, [
        ("متوسط الإيجار للمتر/سنة", f"{avg:,.0f} AED" if avg else "—"),
        ("أقل قيمة في العيّنات", f"{m.get('low'):,} AED" if m.get("low") else "—"),
        ("أعلى قيمة في العيّنات", f"{m.get('high'):,} AED" if m.get("high") else "—"),
        ("حجم العيّنة", str(m.get("sample_size", 0))),
    ]))
    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic(m.get("note", "")), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("شدة المنافسة"), s["ArH1"]))
    story.append(rl["Paragraph"](
        _reshape_arabic(f"التقييم: {c.get('intensity', '—')}  ({c.get('results_found', 0)} نتيجة)"),
        s["ArH2"]))

    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("أبرز المنافسين/المراجع"), s["ArH2"]))
    for r in c.get("top_competitors", [])[:5]:
        title = (r.get("title", "") or "")[:120]
        story.append(rl["Paragraph"](_reshape_arabic(f"• {title}"), s["ArNormal"]))
    for r in m.get("sources", [])[:6]:
        title = (r.get("title", "") or "")[:120]
        story.append(rl["Paragraph"](_reshape_arabic(f"◦ {title}"), s["ArNormal"]))

    doc.build(story)
    return path


def _render_strategic_pdf(intel, path, rl, logo_path):
    doc = rl["SimpleDocTemplate"](str(path), pagesize=rl["A4"],
                                  rightMargin=rl["cm"] * 1.5, leftMargin=rl["cm"] * 1.5,
                                  topMargin=rl["cm"] * 1.5, bottomMargin=rl["cm"] * 1.5)
    s = _styles(rl)
    story = []
    _header(story, rl, logo_path, "التقييم الاستراتيجي")

    st = intel["strategic"]
    swot = st.get("swot", {})

    story.append(rl["Paragraph"](_reshape_arabic("تحليل SWOT"), s["ArH1"]))
    for label, key in [("نقاط القوة", "strengths"), ("نقاط الضعف", "weaknesses"),
                       ("الفرص", "opportunities"), ("التهديدات", "threats")]:
        story.append(rl["Spacer"](1, 0.2 * rl["cm"]))
        story.append(rl["Paragraph"](_reshape_arabic(label), s["ArH2"]))
        for item in swot.get(key, []):
            story.append(rl["Paragraph"](_reshape_arabic(f"• {item}"), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("المخاطر وإجراءات التخفيف"), s["ArH1"]))
    for r in st.get("risks", []):
        story.append(rl["Paragraph"](
            _reshape_arabic(f"⚠️ {r.get('title', '')} — خطورة: {r.get('severity', '')}"),
            s["ArH2"]))
        story.append(rl["Paragraph"](
            _reshape_arabic(f"التخفيف: {r.get('mitigation', '')}"),
            s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.6 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("التوصية المبدئية"), s["ArH1"]))
    story.append(rl["Paragraph"](
        _reshape_arabic(f"{st.get('signal', '')}  القرار: {st.get('decision', '')}"),
        s["ArSignal"]))
    story.append(rl["Paragraph"](
        _reshape_arabic(st.get("rationale", "")),
        s["ArNormal"]))

    doc.build(story)
    return path


def _render_summary_pdf(intel, path, rl, logo_path):
    doc = rl["SimpleDocTemplate"](str(path), pagesize=rl["A4"],
                                  rightMargin=rl["cm"] * 1.5, leftMargin=rl["cm"] * 1.5,
                                  topMargin=rl["cm"] * 1.5, bottomMargin=rl["cm"] * 1.5)
    s = _styles(rl)
    story = []
    _header(story, rl, logo_path, "الملخص التنفيذي — قرار Go / No-Go")

    es = intel["executive_summary"]
    km = es["key_metrics"]

    story.append(rl["Paragraph"](
        _reshape_arabic(f"{es['signal']}  {es['decision']}"),
        s["ArSignal"]))
    story.append(rl["Paragraph"](_reshape_arabic(es["rationale"]), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.4 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("المؤشرات الرئيسية"), s["ArH1"]))
    story.append(_kv_table(rl, [
        ("اسم المناقصة", es["tender_name"]),
        ("الشركة المقدمة", es["company_name"]),
        ("CAPEX", km["capex"]),
        ("الإيراد السنوي", km["annual_revenue"]),
        ("EBITDA السنوي", km["annual_ebitda"]),
        ("IRR", km["irr"]),
        ("Payback", km["payback"]),
        ("NPV @10%", km["npv_10pct"]),
        ("مساحة القطعة", km["plot_area"]),
        ("مدة الإيجار", km["lease_years"]),
        ("سعر الإيجار/م²/سنة", km["rent_per_sqm"]),
        ("مصدر السعر", km["rent_source"]),
    ]))
    story.append(rl["Spacer"](1, 0.4 * rl["cm"]))

    story.append(rl["Paragraph"](_reshape_arabic("توصية التسعير"), s["ArH2"]))
    story.append(rl["Paragraph"](_reshape_arabic(es.get("pricing_recommendation", "")), s["ArNormal"]))

    story.append(rl["PageBreak"]())

    story.append(rl["Paragraph"](_reshape_arabic("أهم 3 نقاط قوة"), s["ArH1"]))
    for item in es.get("top_3_strengths", []):
        story.append(rl["Paragraph"](_reshape_arabic(f"✓ {item}"), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("أهم 3 مخاطر"), s["ArH1"]))
    for item in es.get("top_3_risks", []):
        story.append(rl["Paragraph"](_reshape_arabic(f"⚠️ {item}"), s["ArNormal"]))

    story.append(rl["Spacer"](1, 0.3 * rl["cm"]))
    story.append(rl["Paragraph"](_reshape_arabic("الخطوات التالية"), s["ArH1"]))
    for i, item in enumerate(es.get("next_steps", []), 1):
        story.append(rl["Paragraph"](_reshape_arabic(f"{i}. {item}"), s["ArNormal"]))

    doc.build(story)
    return path


# ----------------------------------------------------------------------------
# Fallback markdown
# ----------------------------------------------------------------------------

def _fallback_markdown(intel: Dict[str, Any], key: str) -> str:
    """Plain markdown when reportlab not available."""
    if key == "technical":
        return intel["technical"]["brief_markdown"]
    if key == "executive_summary":
        es = intel["executive_summary"]
        return f"""# الملخص التنفيذي — Go/No-Go

## القرار: {es['signal']} {es['decision']}

{es['rationale']}

## المؤشرات
- CAPEX: {es['key_metrics']['capex']}
- IRR: {es['key_metrics']['irr']}
- Payback: {es['key_metrics']['payback']}
- NPV: {es['key_metrics']['npv_10pct']}

## توصية التسعير
{es.get('pricing_recommendation', '')}
"""
    import json
    return f"# {key}\n\n```json\n{json.dumps(intel.get(key, {}), ensure_ascii=False, indent=2)}\n```\n"
