"""
Strategic Analyzer
==================
يدمج المخرجات الفنية + المالية + السوقية -> SWOT + المخاطر + توصية أولية.
"""
from __future__ import annotations

from typing import Dict, Any


def run_strategic(
    technical: Dict[str, Any],
    financial: Dict[str, Any],
    market: Dict[str, Any],
    competition: Dict[str, Any],
) -> Dict[str, Any]:
    """Build SWOT + risks + initial recommendation."""

    strengths: list[str] = []
    weaknesses: list[str] = []
    opportunities: list[str] = []
    threats: list[str] = []
    risks: list[Dict[str, str]] = []

    # ----- IRR-based signals -----
    headline = financial.get("headline", {})
    irr = headline.get("irr_pct")
    payback = headline.get("payback_years")
    lease_years = financial.get("assumptions", {}).get("lease_years", 25)

    if irr is not None:
        if irr >= 15:
            strengths.append(f"معدل عائد داخلي ممتاز ({irr}%) فوق متوسط السوق")
        elif irr >= 10:
            strengths.append(f"معدل عائد داخلي مقبول ({irr}%)")
        else:
            weaknesses.append(f"معدل عائد داخلي منخفض ({irr}%)")
            risks.append({
                "title": "عائد منخفض",
                "severity": "عالية",
                "mitigation": "تفاوض على إيجار أرض أقل أو طلب إعفاء سنوات أولى",
            })

    if payback is not None:
        if payback <= lease_years * 0.30:
            strengths.append(f"استرداد رأس المال سريع ({payback} سنة)")
        elif payback >= lease_years * 0.60:
            weaknesses.append(f"فترة استرداد طويلة ({payback} سنة)")
            risks.append({
                "title": "استرداد رأس المال البطيء",
                "severity": "متوسطة",
                "mitigation": "زيادة الإيرادات الثانوية (خدمات، إعلانات) أو خفض CAPEX",
            })

    # ----- Market signals -----
    market_rent = market.get("avg_rent_per_sqm_per_year")
    if market_rent and market.get("sample_size", 0) >= 5:
        strengths.append(f"بيانات سوق موثوقة ({market.get('sample_size')} عيّنة)")

    if market.get("sample_size", 0) < 3:
        weaknesses.append("بيانات سوق محدودة — يحتاج بحث ميداني إضافي")

    # Competition
    intensity = competition.get("intensity", "متوسطة")
    if intensity == "منخفضة":
        opportunities.append("منافسة منخفضة في المنطقة — فرصة لاكتساب حصة سوقية")
    elif intensity == "عالية":
        threats.append("منافسة عالية — يحتاج تمايز قوي في الخدمة أو السعر")
        risks.append({
            "title": "منافسة شديدة",
            "severity": "متوسطة",
            "mitigation": "تطوير نموذج عمل مبتكر أو خدمات مميزة (تأمين، توصيل، عروض اشتراك)",
        })

    # ----- Technical signals -----
    if technical.get("requires_emiratization"):
        threats.append("متطلبات توطين — تأثير على تكلفة الرواتب")
        risks.append({
            "title": "تكلفة التوطين",
            "severity": "متوسطة",
            "mitigation": "تخطيط مبكّر للتوظيف + استخدام دعم نافس",
        })

    if technical.get("requires_sustainability"):
        opportunities.append("متطلبات استدامة — فرصة للحصول على دعم أو شهادات تعزز سمعة الشركة")

    if technical.get("operates_24_7"):
        opportunities.append("تشغيل 24/7 يضاعف الإيرادات السنوية")
        risks.append({
            "title": "تكاليف تشغيل 24/7",
            "severity": "منخفضة",
            "mitigation": "نظام مناوبات + أتمتة + كاميرات ذكية",
        })

    # ----- Build recommendation -----
    fv = financial.get("verdict", {})
    fv_signal = fv.get("signal", "🟡")

    if fv_signal == "🟢" and len(threats) <= len(opportunities):
        decision = "GO"
        signal = "🟢"
        rationale = "المؤشرات المالية إيجابية والمخاطر تحت السيطرة. يُنصح بالتقديم."
    elif fv_signal == "🔴":
        decision = "NO-GO"
        signal = "🔴"
        rationale = "العوائد المتوقعة لا تبرر المخاطرة المالية. لا يُنصح بالتقديم بالشروط الحالية."
    else:
        decision = "CONDITIONAL"
        signal = "🟡"
        rationale = "يمكن التقديم بشرط التفاوض على بنود السعر أو الإعفاءات أو إجراء بحث ميداني إضافي."

    return {
        "swot": {
            "strengths": strengths or ["—"],
            "weaknesses": weaknesses or ["—"],
            "opportunities": opportunities or ["—"],
            "threats": threats or ["—"],
        },
        "risks": risks,
        "decision": decision,
        "signal": signal,
        "rationale": rationale,
    }
