"""
Orchestrator
============
يشغّل الـ5 محللات بتسلسل صحيح ويرجّع dict موحّد كل البيانات للـPDF renderer.
"""
from __future__ import annotations

from typing import Dict, Any
import logging

from . import technical, financial, market, strategic, summary

log = logging.getLogger(__name__)


def run_full_intelligence(
    tender_name: str,
    auction_text: str,
    area_name: str,
    company_name: str,
    user_rent_per_sqm_per_year: float | None = None,
    capex_override: float | None = None,
) -> Dict[str, Any]:
    """
    Main entry point. Returns full intelligence package.

    Parameters
    ----------
    tender_name : اسم المناقصة (للعنوان)
    auction_text : نص الـAuction Document (مستخرج)
    area_name    : المنطقة (Al Shahamah, Al Wathba, إلخ)
    company_name : اسم الشركة المقدمة
    user_rent_per_sqm_per_year : اختياري — لو دخّله المستخدم نستخدمه
    capex_override : اختياري — لو عند المستخدم رقم CAPEX
    """
    log.info("Starting intelligence pipeline for tender=%s area=%s", tender_name, area_name)

    # 1) Technical extraction
    tech_req = technical.extract_requirements(auction_text)
    tech_brief_md = technical.build_technical_brief(tech_req, tender_name)

    # 2) Project type detection
    project_type = financial.detect_project_type(tender_name, tech_req.get("land_use"))

    # 3) Determine plot area & lease years (fall back to safe defaults)
    try:
        plot_area = float(tech_req.get("plot_area") or 0) or 1500.0
    except (TypeError, ValueError):
        plot_area = 1500.0
    try:
        lease_years = int(tech_req.get("lease_term") or 0) or 25
    except (TypeError, ValueError):
        lease_years = 25

    # 4) Market research (only if user didn't provide rent override)
    if user_rent_per_sqm_per_year and user_rent_per_sqm_per_year > 0:
        log.info("Using user-provided rent: %s AED/sqm/yr — skipping market search", user_rent_per_sqm_per_year)
        market_data = {
            "avg_rent_per_sqm_per_year": user_rent_per_sqm_per_year,
            "sample_size": 0,
            "sources": [],
            "low": None,
            "high": None,
            "note": "تم استخدام السعر المُدخَل من المستخدم مباشرة دون بحث.",
        }
        competition_data = market.assess_competition(area_name, project_type)
    else:
        log.info("No user rent provided — running live market research")
        market_data = market.estimate_market_rent(area_name, project_type)
        competition_data = market.assess_competition(area_name, project_type)

    # 5) Financial model
    fin = financial.run_financial(
        plot_area_sqm=plot_area,
        project_type=project_type,
        lease_years=lease_years,
        user_rent_per_sqm_per_year=user_rent_per_sqm_per_year,
        market_avg_rent_per_sqm=market_data.get("avg_rent_per_sqm_per_year"),
        capex_override=capex_override,
    )

    # 6) Strategic SWOT + risks
    strat = strategic.run_strategic(tech_req, fin, market_data, competition_data)

    # 7) Executive summary
    exec_summary = summary.build_executive_summary(
        tender_name=tender_name,
        company_name=company_name,
        technical=tech_req,
        financial=fin,
        market=market_data,
        competition=competition_data,
        strategic=strat,
    )

    return {
        "tender_name": tender_name,
        "area_name": area_name,
        "company_name": company_name,
        "project_type": project_type,
        "technical": {
            "requirements": tech_req,
            "brief_markdown": tech_brief_md,
        },
        "financial": fin,
        "market": market_data,
        "competition": competition_data,
        "strategic": strat,
        "executive_summary": exec_summary,
    }
