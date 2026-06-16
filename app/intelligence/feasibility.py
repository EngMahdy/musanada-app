"""
Volume III - Feasibility Study Generator
=========================================
Builds the formal Feasibility Study PDF that goes INTO the Technical Submission
(not just as a side report). Combines all intelligence outputs into a single
investor-grade document the procuring authority expects to see.

Sections:
1. Executive Summary
2. Project Description & Site Context
3. Market Analysis
4. Technical & Operating Plan
5. Financial Projections (25-year P&L summary)
6. Risk Assessment & Mitigation
7. SWOT Analysis
8. Conclusion & Pricing Strategy
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
from datetime import datetime
import logging

log = logging.getLogger(__name__)


def _try_reportlab():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
            PageBreak,
        )
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT, TA_JUSTIFY
        return locals()
    except ImportError:
        return None


def _reshape(text: str) -> str:
    """Reshape Arabic for proper rendering."""
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display
        return get_display(arabic_reshaper.reshape(text))
    except Exception:
        return text


def build_feasibility_volume(
    intel: Dict[str, Any],
    forms_data: Dict[str, Any],
    output_dir: Path,
    logo_path: Path | None = None,
) -> Path:
    """Generate the formal Volume III - Feasibility Study PDF."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rl = _try_reportlab()
    pdf_path = output_dir / "Volume_III_Feasibility_Study.pdf"

    if rl is None:
        # Markdown fallback
        md = _build_markdown_fallback(intel, forms_data)
        (output_dir / "Volume_III_Feasibility_Study.md").write_text(md, encoding="utf-8")
        return output_dir / "Volume_III_Feasibility_Study.md"

    doc = rl["SimpleDocTemplate"](
        str(pdf_path), pagesize=rl["A4"],
        rightMargin=rl["cm"] * 1.8, leftMargin=rl["cm"] * 1.8,
        topMargin=rl["cm"] * 1.8, bottomMargin=rl["cm"] * 1.8,
        title="Volume III - Feasibility Study",
        author=forms_data.get("company_legal_name", "Bidder"),
    )

    styles = rl["getSampleStyleSheet"]()
    cm = rl["cm"]
    colors_mod = rl["colors"]

    # Custom styles
    h1 = rl["ParagraphStyle"]("H1V3", parent=styles["Heading1"],
                              fontSize=16, alignment=rl["TA_LEFT"],
                              textColor=colors_mod.HexColor("#1F3864"),
                              spaceAfter=10)
    h2 = rl["ParagraphStyle"]("H2V3", parent=styles["Heading2"],
                              fontSize=12, alignment=rl["TA_LEFT"],
                              textColor=colors_mod.HexColor("#C49B30"),
                              spaceAfter=6)
    body = rl["ParagraphStyle"]("BodyV3", parent=styles["Normal"],
                                fontSize=10, alignment=rl["TA_JUSTIFY"],
                                leading=14)
    cover_title = rl["ParagraphStyle"]("Cover", parent=styles["Title"],
                                       fontSize=24, alignment=rl["TA_CENTER"],
                                       textColor=colors_mod.HexColor("#1F3864"))

    story = []

    # ---- Cover Page ----
    if logo_path and Path(logo_path).exists():
        try:
            img = rl["Image"](str(logo_path), width=6 * cm, height=6 * cm)
            img.hAlign = "CENTER"
            story.append(img)
        except Exception:
            pass

    story.append(rl["Spacer"](1, 1 * cm))
    story.append(rl["Paragraph"]("VOLUME III", cover_title))
    story.append(rl["Spacer"](1, 0.3 * cm))
    story.append(rl["Paragraph"]("Feasibility Study", cover_title))
    story.append(rl["Spacer"](1, 0.8 * cm))
    story.append(rl["Paragraph"](
        intel.get("tender_name", ""),
        rl["ParagraphStyle"]("CoverSub", parent=styles["Heading2"],
                             fontSize=14, alignment=rl["TA_CENTER"],
                             textColor=colors_mod.HexColor("#444444"))
    ))
    story.append(rl["Spacer"](1, 1.5 * cm))

    company_name = forms_data.get("company_legal_name") or intel.get("company_name", "Bidder")
    cover_table = rl["Table"]([
        ["Submitted By", company_name],
        ["Authority", "Department of Municipalities & Transport (DMT) / ADIO"],
        ["Project Location", intel.get("area_name", "Abu Dhabi")],
        ["Document Date", datetime.now().strftime("%B %Y")],
        ["Recommendation", f"{intel['strategic'].get('signal', '')} {intel['strategic'].get('decision', '')}"],
    ], colWidths=[5 * cm, 10 * cm])
    cover_table.setStyle(rl["TableStyle"]([
        ("BOX", (0, 0), (-1, -1), 0.75, colors_mod.HexColor("#1F3864")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors_mod.grey),
        ("BACKGROUND", (0, 0), (0, -1), colors_mod.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors_mod.white),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(cover_table)
    story.append(rl["PageBreak"]())

    # ---- Section 1: Executive Summary ----
    es = intel.get("executive_summary", {})
    km = es.get("key_metrics", {})
    story.append(rl["Paragraph"]("1. Executive Summary", h1))
    story.append(rl["Paragraph"](
        f"This Feasibility Study evaluates the {intel.get('project_type', 'commercial')} project "
        f"proposed under the auction <b>{intel.get('tender_name', '')}</b>. Following a comprehensive "
        f"technical, financial, market, and strategic assessment, the recommended action is "
        f"<b>{es.get('decision', 'CONDITIONAL')} {es.get('signal', '')}</b>.",
        body
    ))
    story.append(rl["Spacer"](1, 0.3 * cm))
    story.append(rl["Paragraph"](es.get("rationale", ""), body))
    story.append(rl["Spacer"](1, 0.5 * cm))

    story.append(rl["Paragraph"]("Key Financial Indicators", h2))
    metrics_table = rl["Table"]([
        ["Indicator", "Value"],
        ["CAPEX (Total Capital Expenditure)", km.get("capex", "—")],
        ["Stabilized Annual Revenue", km.get("annual_revenue", "—")],
        ["Stabilized Annual EBITDA", km.get("annual_ebitda", "—")],
        ["Internal Rate of Return (IRR)", km.get("irr", "—")],
        ["Payback Period", km.get("payback", "—")],
        ["Net Present Value @ 10%", km.get("npv_10pct", "—")],
        ["Plot Area", km.get("plot_area", "—")],
        ["Lease Duration", km.get("lease_years", "—")],
        ["Proposed Rent per sqm/year", km.get("rent_per_sqm", "—")],
        ["Rent Source", km.get("rent_source", "—")],
    ], colWidths=[8 * cm, 7 * cm])
    metrics_table.setStyle(rl["TableStyle"]([
        ("GRID", (0, 0), (-1, -1), 0.25, colors_mod.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors_mod.HexColor("#1F3864")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors_mod.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("BACKGROUND", (0, 1), (0, -1), colors_mod.HexColor("#F2F4F8")),
    ]))
    story.append(metrics_table)
    story.append(rl["PageBreak"]())

    # ---- Section 2: Project Description ----
    story.append(rl["Paragraph"]("2. Project Description & Site Context", h1))
    tech = intel.get("technical", {}).get("requirements", {})
    story.append(rl["Paragraph"](
        f"The project entails the design, construction, and operation of a "
        f"<b>{intel.get('project_type', 'commercial')}</b> facility on a "
        f"<b>{tech.get('plot_area') or km.get('plot_area', '—')} sqm</b> plot "
        f"located in <b>{intel.get('area_name', '—')}</b>. The lease term is "
        f"<b>{tech.get('lease_term') or km.get('lease_years', '25')} years</b> "
        f"with a construction window of {tech.get('construction_period') or '18 months'}.",
        body
    ))
    story.append(rl["Spacer"](1, 0.4 * cm))

    story.append(rl["Paragraph"]("Regulatory & Compliance Highlights", h2))
    compliance_items = [
        f"{'Required' if tech.get('requires_emiratization') else 'Not explicitly required'} — Emiratization compliance",
        f"{'Required' if tech.get('requires_sustainability') else 'Not explicitly required'} — Sustainability (Estidama/LEED)",
        f"{'Required' if tech.get('operates_24_7') else 'Not required'} — 24/7 Operations",
        f"ICV Target: {tech.get('icv_requirement') or '—'}%",
        f"Bid Bond: {tech.get('bid_bond') or '—'} AED",
        f"Performance Bond: {tech.get('performance_bond') or '—'}%",
    ]
    for item in compliance_items:
        story.append(rl["Paragraph"](f"• {item}", body))
    story.append(rl["PageBreak"]())

    # ---- Section 3: Market Analysis ----
    story.append(rl["Paragraph"]("3. Market Analysis", h1))
    m = intel.get("market", {})
    c = intel.get("competition", {})
    story.append(rl["Paragraph"](
        f"A live market scan was conducted across Bayut, Dubizzle, and adjacent classified channels "
        f"to benchmark commercial rents in <b>{intel.get('area_name', '—')}</b>. "
        f"{m.get('sample_size', 0)} comparable data points were collected. "
        f"Median annual rent estimated at <b>{m.get('avg_rent_per_sqm_per_year') or '—'} AED/sqm/year</b>, "
        f"with a low-high range of {m.get('low', '—')}–{m.get('high', '—')} AED.",
        body
    ))
    story.append(rl["Spacer"](1, 0.3 * cm))
    story.append(rl["Paragraph"]("Competitive Landscape", h2))
    story.append(rl["Paragraph"](
        f"Competition intensity is rated as <b>{c.get('intensity', '—')}</b> "
        f"({c.get('results_found', 0)} relevant operators identified in the catchment area). "
        "This informs both pricing strategy and service differentiation requirements.",
        body
    ))
    story.append(rl["Spacer"](1, 0.3 * cm))
    if m.get("note"):
        story.append(rl["Paragraph"](f"<i>Note: {m.get('note')}</i>", body))
    story.append(rl["PageBreak"]())

    # ---- Section 4: Technical & Operating Plan ----
    story.append(rl["Paragraph"]("4. Technical & Operating Plan", h1))
    operating = forms_data.get("operating_model") or "Operations plan to be developed in line with the project's strategic positioning."
    for para in str(operating).split("\n\n"):
        if para.strip():
            story.append(rl["Paragraph"](para.strip(), body))
            story.append(rl["Spacer"](1, 0.2 * cm))
    story.append(rl["PageBreak"]())

    # ---- Section 5: Financial Projections ----
    story.append(rl["Paragraph"]("5. Financial Projections", h1))
    story.append(rl["Paragraph"]("Year-by-Year Cash Flow Summary (AED)", h2))
    yearly = intel.get("financial", {}).get("yearly_table", [])
    if yearly:
        data = [["Year", "Occupancy", "Revenue", "OPEX", "EBITDA", "Tax", "Net Cash Flow"]]
        for r in yearly[:25]:
            data.append([
                str(r["year"]),
                f"{r['occupancy_pct']}%",
                f"{r['revenue']:,.0f}",
                f"{r['opex']:,.0f}",
                f"{r['ebitda']:,.0f}",
                f"{r['tax']:,.0f}",
                f"{r['net_cash_flow']:,.0f}",
            ])
        t = rl["Table"](data, repeatRows=1)
        t.setStyle(rl["TableStyle"]([
            ("GRID", (0, 0), (-1, -1), 0.25, colors_mod.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors_mod.HexColor("#1F3864")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors_mod.white),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(t)
    story.append(rl["PageBreak"]())

    # ---- Section 6: Risk Assessment ----
    story.append(rl["Paragraph"]("6. Risk Assessment & Mitigation", h1))
    risks = intel.get("strategic", {}).get("risks", [])
    if risks:
        data = [["Risk", "Severity", "Mitigation"]]
        for r in risks:
            data.append([
                r.get("title", ""),
                r.get("severity", ""),
                r.get("mitigation", ""),
            ])
        t = rl["Table"](data, colWidths=[4 * cm, 2.5 * cm, 8.5 * cm], repeatRows=1)
        t.setStyle(rl["TableStyle"]([
            ("GRID", (0, 0), (-1, -1), 0.25, colors_mod.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors_mod.HexColor("#1F3864")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors_mod.white),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(t)
    else:
        story.append(rl["Paragraph"]("No material risks identified at this stage.", body))
    story.append(rl["Spacer"](1, 0.5 * cm))

    # ---- Section 7: SWOT ----
    story.append(rl["Paragraph"]("7. SWOT Analysis", h1))
    swot = intel.get("strategic", {}).get("swot", {})
    swot_table = rl["Table"]([
        ["Strengths", "Weaknesses"],
        [
            "\n".join(f"• {s}" for s in swot.get("strengths", [])),
            "\n".join(f"• {s}" for s in swot.get("weaknesses", [])),
        ],
        ["Opportunities", "Threats"],
        [
            "\n".join(f"• {s}" for s in swot.get("opportunities", [])),
            "\n".join(f"• {s}" for s in swot.get("threats", [])),
        ],
    ], colWidths=[7.5 * cm, 7.5 * cm])
    swot_table.setStyle(rl["TableStyle"]([
        ("GRID", (0, 0), (-1, -1), 0.25, colors_mod.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors_mod.HexColor("#1F3864")),
        ("BACKGROUND", (0, 2), (-1, 2), colors_mod.HexColor("#C49B30")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors_mod.white),
        ("TEXTCOLOR", (0, 2), (-1, 2), colors_mod.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(swot_table)
    story.append(rl["PageBreak"]())

    # ---- Section 8: Conclusion & Pricing Strategy ----
    story.append(rl["Paragraph"]("8. Conclusion & Pricing Strategy", h1))
    story.append(rl["Paragraph"](
        f"Based on the integrated analysis, the project demonstrates "
        f"<b>{intel['strategic'].get('decision', 'CONDITIONAL').lower()}</b> "
        "viability under the assumptions used. The strategic recommendation is to:",
        body
    ))
    story.append(rl["Spacer"](1, 0.3 * cm))
    story.append(rl["Paragraph"]("Pricing Recommendation", h2))
    story.append(rl["Paragraph"](es.get("pricing_recommendation", "—"), body))
    story.append(rl["Spacer"](1, 0.4 * cm))
    story.append(rl["Paragraph"]("Proposed Next Steps", h2))
    for i, step in enumerate(es.get("next_steps", []), 1):
        story.append(rl["Paragraph"](f"{i}. {step}", body))

    # ---- Disclaimer ----
    story.append(rl["Spacer"](1, 0.8 * cm))
    story.append(rl["Paragraph"](
        "<i>This Feasibility Study has been prepared by Musanada Engineering Consultancy & "
        "Feasibility Studies on the basis of information available at the time of preparation. "
        "Actual results may vary based on market conditions, regulatory changes, and "
        "implementation factors.</i>",
        rl["ParagraphStyle"]("Disclaimer", parent=body, fontSize=8,
                             textColor=colors_mod.grey)
    ))

    doc.build(story)
    log.info("Feasibility Volume III generated: %s", pdf_path)
    return pdf_path


def _build_markdown_fallback(intel, forms_data) -> str:
    es = intel.get("executive_summary", {})
    km = es.get("key_metrics", {})
    return f"""# Volume III - Feasibility Study

## {intel.get('tender_name', '')}

**Submitted By:** {forms_data.get('company_legal_name', '')}
**Recommendation:** {es.get('signal', '')} {es.get('decision', '')}

## Executive Summary
{es.get('rationale', '')}

## Key Metrics
- CAPEX: {km.get('capex')}
- Annual Revenue: {km.get('annual_revenue')}
- IRR: {km.get('irr')}
- Payback: {km.get('payback')}
- NPV: {km.get('npv_10pct')}

## Pricing Recommendation
{es.get('pricing_recommendation', '')}
"""
