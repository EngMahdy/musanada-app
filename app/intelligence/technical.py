"""
Technical Analyzer
==================
يستخرج المتطلبات الفنية من نص المناقصة (Auction Document) ويولّد Brief PDF.
"""
from __future__ import annotations

import re
from typing import Dict, Any


_PATTERNS = {
    "plot_area": [
        r"(?:plot\s*area|total\s*area|land\s*area|site\s*area)[^\d]*([\d,\.]+)\s*(?:sqm|m2|m²|square\s*meters?)",
        r"(?:المساحة|مساحة\s*القطعة)[^\d]*([\d,\.]+)\s*(?:م2|م²|متر\s*مربع)",
    ],
    "lease_term": [
        r"(?:lease\s*term|lease\s*period|duration\s*of\s*lease)[^\d]*(\d+)\s*(?:years?|yrs?)",
        r"(?:مدة\s*الإيجار|مدة\s*العقد)[^\d]*(\d+)\s*سنة",
    ],
    "construction_period": [
        r"(?:construction\s*period|build\s*period|completion\s*within)[^\d]*(\d+)\s*(?:months?|years?)",
        r"(?:مدة\s*البناء|فترة\s*الإنشاء)[^\d]*(\d+)\s*(?:شهر|سنة)",
    ],
    "auction_type": [
        r"(?:auction\s*type|tender\s*type)[\s:]*([A-Za-z\s]+)",
    ],
    "land_use": [
        r"(?:land\s*use|permitted\s*use|intended\s*use)[\s:]*([A-Za-z\s,&/-]+)",
    ],
    "icv_requirement": [
        r"(?:ICV|in[-\s]?country\s*value)[^\d]*(\d+(?:\.\d+)?)\s*%?",
    ],
    "bid_bond": [
        r"(?:bid\s*bond|tender\s*bond)[^\d]*([\d,]+)\s*AED",
    ],
    "performance_bond": [
        r"(?:performance\s*bond)[^\d]*(\d+(?:\.\d+)?)\s*%",
    ],
}


def _first_match(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(1).strip().replace(",", "")
    return None


def extract_requirements(auction_text: str) -> Dict[str, Any]:
    """Extract structured technical requirements from auction document text."""
    out: Dict[str, Any] = {}
    text = auction_text or ""
    for key, pats in _PATTERNS.items():
        out[key] = _first_match(text, pats)

    # Heuristic flags
    lower = text.lower()
    out["requires_emiratization"] = bool(re.search(r"emirati|emiratisation|emiratization|توطين", text, re.IGNORECASE))
    out["requires_sustainability"] = bool(re.search(r"sustainab|leed|estidama|البيئة|الاستدامة", text, re.IGNORECASE))
    out["operates_24_7"] = "24/7" in lower or "24 hours" in lower or "round the clock" in lower
    return out


def build_technical_brief(req: Dict[str, Any], tender_name: str) -> str:
    """Build a markdown technical brief that can be rendered to PDF."""
    plot = req.get("plot_area") or "غير محدد"
    lease = req.get("lease_term") or "غير محدد"
    construction = req.get("construction_period") or "غير محدد"
    use = req.get("land_use") or "غير محدد"
    icv = req.get("icv_requirement") or "—"
    bond = req.get("bid_bond") or "—"
    perf = req.get("performance_bond") or "—"

    md = f"""# التحليل الفني — {tender_name}

## 📐 المواصفات الأساسية

| البند | القيمة |
|---|---|
| مساحة القطعة | {plot} م² |
| مدة الإيجار | {lease} سنة |
| مدة الإنشاء | {construction} |
| الاستخدام المسموح | {use} |
| متطلب ICV | {icv}% |
| ضمان العطاء | {bond} AED |
| ضمان الأداء | {perf}% |

## ⚠️ المتطلبات الخاصة

- {'✅' if req.get('requires_emiratization') else '➖'} **التوطين (Emiratization):** {'مطلوب' if req.get('requires_emiratization') else 'غير مذكور صراحة'}
- {'✅' if req.get('requires_sustainability') else '➖'} **الاستدامة (Estidama/LEED):** {'مطلوب' if req.get('requires_sustainability') else 'غير مذكور صراحة'}
- {'✅' if req.get('operates_24_7') else '➖'} **التشغيل 24/7:** {'مطلوب' if req.get('operates_24_7') else 'غير مطلوب'}

## 🔧 التوصيات الفنية

1. تأكد من توافق التصميم مع الاستخدام المسموح به في كروكي الموقع
2. خصص في الميزانية بند ICV لو متطلب (عادة 10-15% من قيمة العقد)
3. ضع جدول زمني تفصيلي للإنشاء يتوافق مع المدة المسموحة
4. تجهيز ضمان العطاء البنكي قبل تاريخ التقديم بأسبوع على الأقل
"""
    return md
