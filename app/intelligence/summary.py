"""
Executive Summary (Go/No-Go) Generator
======================================
صفحتين A4 - القرار النهائي بشكل مكثف.
"""
from __future__ import annotations

from typing import Dict, Any


def build_executive_summary(
    tender_name: str,
    company_name: str,
    technical: Dict[str, Any],
    financial: Dict[str, Any],
    market: Dict[str, Any],
    competition: Dict[str, Any],
    strategic: Dict[str, Any],
) -> Dict[str, Any]:
    """Compose executive summary structure used by the PDF renderer."""

    h = financial.get("headline", {})
    a = financial.get("assumptions", {})

    irr = h.get("irr_pct")
    payback = h.get("payback_years")
    capex = h.get("capex", 0)
    revenue = h.get("annual_revenue_stabilized", 0)
    ebitda = h.get("annual_ebitda_stabilized", 0)
    npv = h.get("npv_aed", 0)

    proposed_price = None
    if irr is not None and irr < 10:
        # Suggest reducing offered annual rent to landlord by 15-20%
        proposed_price = "خفّض السعر المقترح بنسبة 15-20% أو اطلب إعفاء أول سنتين"
    elif irr is not None and irr >= 15:
        proposed_price = "السعر المقترح في الـ Auction Document مناسب — يمكن المنافسة بثقة"
    else:
        proposed_price = "السعر مقبول مع هامش تفاوض محدود (5-10%)"

    return {
        "tender_name": tender_name,
        "company_name": company_name,
        "decision": strategic.get("decision", "CONDITIONAL"),
        "signal": strategic.get("signal", "🟡"),
        "rationale": strategic.get("rationale", ""),
        "key_metrics": {
            "capex": f"{capex:,.0f} AED",
            "annual_revenue": f"{revenue:,.0f} AED",
            "annual_ebitda": f"{ebitda:,.0f} AED",
            "irr": f"{irr}%" if irr is not None else "غير محسوب",
            "payback": f"{payback} سنة" if payback else "غير محسوب",
            "npv_10pct": f"{npv:,.0f} AED",
            "lease_years": f"{a.get('lease_years', '—')} سنة",
            "plot_area": f"{a.get('plot_area_sqm', '—')} م²",
            "rent_per_sqm": f"{a.get('rent_per_sqm_per_year', '—')} AED/م²/سنة",
            "rent_source": a.get("rent_source", "—"),
        },
        "pricing_recommendation": proposed_price,
        "top_3_strengths": strategic.get("swot", {}).get("strengths", [])[:3],
        "top_3_risks": [
            f"{r.get('title', '')} ({r.get('severity', '')})"
            for r in strategic.get("risks", [])[:3]
        ],
        "market_summary": {
            "samples": market.get("sample_size", 0),
            "low": market.get("low"),
            "high": market.get("high"),
            "competition_intensity": competition.get("intensity", "—"),
        },
        "next_steps": _next_steps(strategic.get("decision", "CONDITIONAL")),
    }


def _next_steps(decision: str) -> list[str]:
    if decision == "GO":
        return [
            "تجهيز كل النماذج وتقديمها قبل الموعد النهائي",
            "تجهيز ضمان العطاء البنكي (Bid Bond)",
            "تثبيت السعر المقترح بناءً على التحليل المالي",
            "تجهيز فريق الإنشاء والتشغيل بشكل مبدئي",
        ]
    if decision == "NO-GO":
        return [
            "إبلاغ القرار بعدم التقديم وحفظ التحليل كمرجع",
            "متابعة مناقصات مشابهة بشروط أفضل",
            "النظر في إعادة التقييم لو تم تخفيض السعر المطلوب",
        ]
    return [
        "التواصل مع جهة المناقصة لتوضيح بنود معينة",
        "إجراء زيارة ميدانية للموقع وتقييم المنافسة",
        "تجهيز خطاب تفاوض على بنود السعر أو الإعفاءات",
        "اتخاذ القرار النهائي قبل 48 ساعة من الموعد",
    ]
