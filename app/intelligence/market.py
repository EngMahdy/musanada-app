"""
Market Research Analyzer
========================
يبحث على Bayut و Dubizzle (من خلال Google) ليجد متوسط أسعار الإيجار
في المنطقة + يقيّم المنافسة من خرائط جوجل (proxy عبر Google Search).

ملاحظة: لا يحتاج API keys مدفوعة — يعتمد على HTML scraping من نتائج Google
عبر DuckDuckGo (لتجنّب CAPTCHA) أو requests مع User-Agent عادي.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, Any, List
import requests

log = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _ddg_search(query: str, max_results: int = 8) -> List[Dict[str, str]]:
    """Light DuckDuckGo HTML search (no API key)."""
    try:
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": query},
            headers={"User-Agent": USER_AGENT},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        # Very simple regex extract — DDG returns <a class="result__a"
        hits = re.findall(
            r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            r.text, re.IGNORECASE | re.DOTALL,
        )
        results = []
        for url, title in hits[:max_results]:
            # strip HTML tags from title
            clean_title = re.sub(r"<[^>]+>", "", title).strip()
            results.append({"url": url, "title": clean_title})
        return results
    except Exception as e:  # pragma: no cover
        log.warning("DDG search failed: %s", e)
        return []


def _extract_aed_amounts(text: str) -> List[int]:
    """Pull AED numbers from text — used to estimate rent ranges."""
    amounts = []
    for m in re.finditer(r"AED\s*([\d,]+)|([\d,]+)\s*AED", text, re.IGNORECASE):
        raw = (m.group(1) or m.group(2) or "").replace(",", "")
        if raw.isdigit():
            n = int(raw)
            # filter sensible commercial annual rent range (5K – 5M AED)
            if 5_000 <= n <= 5_000_000:
                amounts.append(n)
    return amounts


def estimate_market_rent(area_name: str, project_type: str) -> Dict[str, Any]:
    """
    Search live web for annual rent per sqm in the given Abu Dhabi area.
    Returns dict with avg, low, high, sources.
    """
    type_kw = {
        "automotive": "auto service center workshop",
        "retail": "retail shop commercial",
        "sports": "sports facility gym",
        "industrial": "industrial warehouse",
        "food_truck": "food truck park",
        "default": "commercial",
    }.get(project_type, "commercial")

    queries = [
        f"{type_kw} for rent {area_name} Abu Dhabi annual price AED sqm site:bayut.com",
        f"{type_kw} commercial rent {area_name} Abu Dhabi site:dubizzle.com",
        f"commercial rent prices {area_name} Abu Dhabi 2026",
    ]

    all_results: List[Dict[str, str]] = []
    all_amounts: List[int] = []
    for q in queries:
        results = _ddg_search(q, max_results=5)
        all_results.extend(results)
        for r in results:
            all_amounts.extend(_extract_aed_amounts(r["title"]))

    if not all_amounts:
        return {
            "avg_rent_per_sqm_per_year": None,
            "low": None,
            "high": None,
            "sample_size": 0,
            "sources": all_results[:6],
            "note": "لم يتم العثور على بيانات إيجار مباشرة في نتائج البحث. سيتم استخدام متوسط افتراضي محافظ.",
        }

    all_amounts.sort()
    median_amount = all_amounts[len(all_amounts) // 2]

    # The amounts found are usually total annual rent for a property.
    # We estimate a rough per-sqm if we assume typical commercial unit is 200-500 sqm
    # — this is conservative; user should override if known.
    estimated_per_sqm = median_amount / 300

    return {
        "avg_rent_per_sqm_per_year": round(estimated_per_sqm, 2),
        "low": min(all_amounts),
        "high": max(all_amounts),
        "sample_size": len(all_amounts),
        "sources": all_results[:6],
        "note": (
            f"تقدير مبني على {len(all_amounts)} عيّنة من Bayut/Dubizzle لمنطقة {area_name}. "
            "الرقم تقريبي ويفضّل مراجعته بزيارة ميدانية."
        ),
    }


def assess_competition(area_name: str, project_type: str) -> Dict[str, Any]:
    """Quick competition check: count similar businesses in the area via search."""
    type_kw = {
        "automotive": "auto service workshop garage",
        "retail": "supermarket grocery shop",
        "sports": "gym sports club fitness",
        "industrial": "warehouse industrial",
        "food_truck": "food truck restaurant",
        "default": "commercial",
    }.get(project_type, "commercial")

    q = f"{type_kw} {area_name} Abu Dhabi"
    results = _ddg_search(q, max_results=10)
    return {
        "search_query": q,
        "results_found": len(results),
        "top_competitors": results[:5],
        "intensity": (
            "عالية" if len(results) >= 8 else
            "متوسطة" if len(results) >= 4 else
            "منخفضة"
        ),
    }
