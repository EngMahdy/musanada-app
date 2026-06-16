"""
Financial Analyzer
==================
يحسب CAPEX / OPEX / Revenue / IRR / NPV / Payback Period.
يستخدم سعر الإيجار المُدخَل من المستخدم لو متاح، وإلا متوسط السوق من market.py
"""
from __future__ import annotations

from typing import Dict, Any, List
from datetime import datetime


# Default benchmarks for Abu Dhabi commercial projects (AED)
DEFAULT_CAPEX_PER_SQM = {
    "automotive": 2800,    # AED/sqm for auto service centers
    "retail": 3500,        # AED/sqm for retail/supermarket
    "sports": 4500,        # AED/sqm for integrated sports facilities
    "industrial": 2200,    # AED/sqm for mini-industrial
    "food_truck": 1800,    # AED/sqm for food truck parks (lighter build)
    "default": 3000,
}
DEFAULT_OPEX_RATE = 0.18    # 18% of revenue
DEFAULT_DISCOUNT_RATE = 0.10  # 10% for NPV
TAX_RATE = 0.09             # 9% UAE corporate tax (above AED 375K profit)


def detect_project_type(tender_name: str, land_use: str | None) -> str:
    """Heuristic project type detection from tender name/usage."""
    t = (tender_name or "").lower() + " " + (land_use or "").lower()
    if any(k in t for k in ["automotive", "auto", "garage", "car service", "service center"]):
        return "automotive"
    if any(k in t for k in ["retail", "supermarket", "shop", "mall"]):
        return "retail"
    if any(k in t for k in ["sport", "sports facility", "gym", "fitness"]):
        return "sports"
    if any(k in t for k in ["industrial", "warehouse", "factory"]):
        return "industrial"
    if any(k in t for k in ["food truck", "food park", "kiosk"]):
        return "food_truck"
    return "default"


def compute_irr(cash_flows: List[float], guess: float = 0.1, max_iter: int = 200) -> float | None:
    """Newton-Raphson IRR. Returns None if it doesn't converge."""
    rate = guess
    for _ in range(max_iter):
        npv = sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))
        d_npv = sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows))
        if abs(d_npv) < 1e-12:
            return None
        new_rate = rate - npv / d_npv
        if abs(new_rate - rate) < 1e-7:
            return new_rate
        rate = new_rate
        if rate < -0.99:
            return None
    return None


def run_financial(
    plot_area_sqm: float,
    project_type: str,
    lease_years: int,
    user_rent_per_sqm_per_year: float | None,
    market_avg_rent_per_sqm: float | None,
    annual_rent_to_landlord: float = 0.0,
    capex_override: float | None = None,
) -> Dict[str, Any]:
    """
    Returns full financial model.

    rent_per_sqm_per_year priority:
        1. user_rent_per_sqm_per_year (if provided)
        2. market_avg_rent_per_sqm   (from web search)
        3. fallback default per type
    """
    # 1) Determine effective rent assumption
    if user_rent_per_sqm_per_year and user_rent_per_sqm_per_year > 0:
        rent_per_sqm = user_rent_per_sqm_per_year
        rent_source = "مُدخَل من المستخدم"
    elif market_avg_rent_per_sqm and market_avg_rent_per_sqm > 0:
        rent_per_sqm = market_avg_rent_per_sqm
        rent_source = "بحث ويب حي (Market Research)"
    else:
        # conservative fallback per project type
        fallback = {"automotive": 600, "retail": 1200, "sports": 400,
                    "industrial": 350, "food_truck": 800, "default": 700}
        rent_per_sqm = fallback.get(project_type, 700)
        rent_source = "متوسط افتراضي محافظ"

    # 2) CAPEX
    capex_per_sqm = DEFAULT_CAPEX_PER_SQM.get(project_type, DEFAULT_CAPEX_PER_SQM["default"])
    capex = capex_override if capex_override else plot_area_sqm * capex_per_sqm

    # 3) Annual revenue (assume 80% occupancy in stabilized years)
    gross_revenue_full = plot_area_sqm * rent_per_sqm
    secondary_revenue = gross_revenue_full * 0.15   # services + advertising + parking
    total_gross_revenue_full = gross_revenue_full + secondary_revenue

    # 4) OPEX (% of revenue) + annual rent to landlord/DMT
    annual_opex = total_gross_revenue_full * DEFAULT_OPEX_RATE + annual_rent_to_landlord

    # 5) Build year-by-year cashflows (lease_years)
    rows = []
    cashflows: List[float] = [-capex]   # year 0
    ramp_curve = [0.55, 0.75, 0.90, 1.00]  # 4-year ramp to stabilization
    for y in range(1, lease_years + 1):
        occupancy = ramp_curve[min(y - 1, len(ramp_curve) - 1)]
        revenue_y = total_gross_revenue_full * occupancy
        opex_y = revenue_y * DEFAULT_OPEX_RATE + annual_rent_to_landlord
        ebitda_y = revenue_y - opex_y
        tax_y = max(0, (ebitda_y - 375000) * TAX_RATE)
        net_y = ebitda_y - tax_y
        cashflows.append(net_y)
        rows.append({
            "year": y,
            "occupancy_pct": round(occupancy * 100, 1),
            "revenue": round(revenue_y, 0),
            "opex": round(opex_y, 0),
            "ebitda": round(ebitda_y, 0),
            "tax": round(tax_y, 0),
            "net_cash_flow": round(net_y, 0),
        })

    # 6) Metrics
    irr = compute_irr(cashflows)
    npv = sum(cf / (1 + DEFAULT_DISCOUNT_RATE) ** i for i, cf in enumerate(cashflows))

    # Payback: cumulative cashflow first turns positive
    cum = 0.0
    payback_year = None
    for i, cf in enumerate(cashflows):
        cum += cf
        if cum >= 0 and i > 0:
            payback_year = i
            break

    total_net_profit = sum(cashflows)

    return {
        "assumptions": {
            "plot_area_sqm": plot_area_sqm,
            "project_type": project_type,
            "lease_years": lease_years,
            "rent_per_sqm_per_year": round(rent_per_sqm, 2),
            "rent_source": rent_source,
            "capex_per_sqm": capex_per_sqm,
            "opex_rate_of_revenue": DEFAULT_OPEX_RATE,
            "discount_rate": DEFAULT_DISCOUNT_RATE,
            "tax_rate": TAX_RATE,
        },
        "headline": {
            "capex": round(capex, 0),
            "annual_revenue_stabilized": round(total_gross_revenue_full, 0),
            "annual_opex_stabilized": round(annual_opex, 0),
            "annual_ebitda_stabilized": round(total_gross_revenue_full - annual_opex, 0),
            "irr_pct": round(irr * 100, 2) if irr is not None else None,
            "npv_aed": round(npv, 0),
            "payback_years": payback_year,
            "total_net_profit_lease": round(total_net_profit, 0),
        },
        "yearly_table": rows,
        "verdict": _financial_verdict(irr, payback_year, lease_years),
    }


def _financial_verdict(irr: float | None, payback: int | None, lease_years: int) -> Dict[str, str]:
    """Quick financial verdict signal."""
    if irr is None or payback is None:
        return {"signal": "🟡", "label": "بيانات غير كافية"}
    if irr >= 0.15 and payback <= lease_years * 0.35:
        return {"signal": "🟢", "label": "ممتاز — استثمار مغرٍ"}
    if irr >= 0.10 and payback <= lease_years * 0.50:
        return {"signal": "🟢", "label": "جيد — يستحق التقديم"}
    if irr >= 0.07:
        return {"signal": "🟡", "label": "مقبول — يحتاج تفاوض على السعر"}
    return {"signal": "🔴", "label": "ضعيف — لا يُنصح بالتقديم بهذا السعر"}
