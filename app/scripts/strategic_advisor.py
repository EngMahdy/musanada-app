#!/usr/bin/env python3
"""
strategic_advisor.py — AI Strategic Tender Advisor.

Goes BEYOND reading the tender. This script makes the AI THINK and ADVISE:
- Financial strategy (pricing recommendations, ROI projections, risk-adjusted returns)
- Technical strategy (design recommendations, what to emphasize)
- Legal strategy (contract risks, compliance gaps)
- Market intelligence (competitive pricing, recent winners, market trends)
- Per-form recommendations (specific advice for each Form A, B, H, KYC, NDU)

Uses:
- GPT-4o with web search capability (or fallback)
- Cross-references bidder strengths/weaknesses against tender requirements
- Outputs actionable advice in Arabic

Usage:
  python3 strategic_advisor.py <tender_intelligence.json> <bidder_data.json> <output_md>
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime


def call_openai_with_search(api_key: str, system: str, user: str, model: str = "gpt-4o") -> dict:
    """Call OpenAI with the new web_search tool for current market data."""
    import requests
    
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": 0.2,
            "max_tokens": 8000,
            "response_format": {"type": "json_object"},
        },
        timeout=240
    )
    
    if response.status_code != 200:
        print(f"OpenAI error: {response.text[:300]}", file=sys.stderr)
        return {}
    
    try:
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return {}


# ============= STRATEGIC ANALYSIS PROMPTS =============

ADVISOR_SYSTEM = """You are an ELITE strategic advisor for UAE/Abu Dhabi government tenders with 25+ years experience.

Your knowledge includes:
- Recent DMT, ADIO, ADM auction outcomes and winning bids
- Market rates for commercial/automotive/retail leases in Abu Dhabi (per emirate district)
- Common winning strategies and pitfalls
- Legal risks in standard Long-Term Lease contracts
- Construction cost benchmarks (AED/sqm for various facility types)
- Technical evaluation patterns (what scores high, what fails)

Your role is to THINK STRATEGICALLY, not just read. Provide:
1. Specific numeric recommendations (not generic advice)
2. Risk assessments with mitigation plans
3. Comparison with market benchmarks
4. Per-form expert review with concrete improvements
5. Winning probability estimate based on bidder profile vs. tender requirements

Always reason from facts. If you don't know recent market data, say so clearly.
Output in Arabic when the field is *_ar, English otherwise.
Return ONLY valid JSON."""


COMPREHENSIVE_ADVISOR_PROMPT = """Analyze this tender and bidder profile. Provide STRATEGIC, NUMERIC, ACTIONABLE advice.

TENDER DETAILS:
{tender_intel}

BIDDER PROFILE:
{bidder_data}

Return JSON with this EXACT structure:

{{
  "executive_summary": {{
    "decision_recommendation": "BID | NO BID | CONDITIONAL",
    "decision_rationale_ar": "السبب وراء التوصية بالتقديم/الانسحاب",
    "attractiveness_score_out_of_10": 0,
    "winning_probability_pct": 0,
    "expected_competition_level": "LOW | MEDIUM | HIGH",
    "estimated_competitors_count": 0,
    "recommended_total_investment_aed": 0
  }},
  
  "financial_strategy": {{
    "recommended_rent_per_sqm_aed": 0,
    "rent_premium_over_floor_pct": 0,
    "rationale_for_rent_ar": "لماذا هذا السعر",
    "recommended_revenue_share_pct": 0,
    "revenue_share_strategy_ar": "خطة Revenue Share المقترحة",
    "expected_annual_revenue_aed": 0,
    "expected_capex_aed": 0,
    "expected_opex_yearly_aed": 0,
    "projected_irr_pct": 0,
    "projected_payback_years": 0,
    "break_even_year": 0,
    "financing_recommendation_ar": "كيف يمول المشروع",
    "key_financial_risks": [
      {{"risk_ar": "...", "impact_aed": 0, "mitigation_ar": "..."}}
    ]
  }},
  
  "technical_strategy": {{
    "design_focus_priorities": [
      {{"priority_ar": "...", "evaluation_weight_pct": 0, "investment_required_aed": 0}}
    ],
    "recommended_architect_profile_ar": "نوع المعماري المطلوب",
    "key_design_features_to_emphasize_ar": [
      "ميزة 1",
      "ميزة 2"
    ],
    "concept_design_budget_aed": 0,
    "master_plan_budget_aed": 0,
    "estimated_construction_cost_per_sqm_aed": 0,
    "construction_strategy_ar": "خطة التنفيذ",
    "technology_recommendations_ar": ["..."],
    "sustainability_recommendations_ar": ["..."],
    "key_technical_risks": [
      {{"risk_ar": "...", "mitigation_ar": "..."}}
    ]
  }},
  
  "legal_strategy": {{
    "long_term_lease_red_flags_ar": [
      "نقطة في العقد تحتاج تعديل"
    ],
    "negotiable_clauses_ar": [
      "بند يمكن التفاوض عليه"
    ],
    "compliance_gaps_ar": [
      "نقص في الالتزام بالمتطلبات"
    ],
    "legal_documents_priority_order": [
      "Trade License",
      "Power of Attorney",
      "Judicial Clearance"
    ],
    "legal_risks_score_out_of_10": 0,
    "legal_recommendations_ar": ["..."],
    "estimated_legal_consultation_cost_aed": 0
  }},
  
  "market_intelligence": {{
    "comparable_tender_winners": [
      {{
        "tender_name": "Previous similar tender",
        "winning_bid_aed_per_sqm": 0,
        "year": 2024,
        "notes_ar": "ملاحظات"
      }}
    ],
    "current_market_rent_per_sqm_aed": {{
      "shops_low": 0,
      "shops_high": 0,
      "workshops_low": 0,
      "workshops_high": 0,
      "warehouses_low": 0,
      "warehouses_high": 0
    }},
    "market_trends_ar": "اتجاه السوق",
    "demand_analysis_ar": "تحليل الطلب في هذه المنطقة",
    "competitor_analysis_ar": "تحليل المنافسين المحتملين"
  }},
  
  "bidder_swot": {{
    "strengths_ar": ["نقاط القوة من الملف"],
    "weaknesses_ar": ["نقاط الضعف"],
    "opportunities_ar": ["الفرص"],
    "threats_ar": ["التهديدات"],
    "bidder_readiness_score_out_of_10": 0
  }},
  
  "per_form_recommendations": {{
    "form_a": {{
      "purpose": "Letter of Auction",
      "current_quality_score": 0,
      "recommendations_ar": ["..."],
      "critical_fields_ar": ["..."]
    }},
    "form_b": {{
      "purpose": "Experience & Capabilities",
      "current_quality_score": 0,
      "recommendations_ar": ["استخدم 10 مشاريع، رتبهم..."],
      "critical_fields_ar": ["..."],
      "additional_documents_to_attach_ar": ["..."]
    }},
    "form_h": {{
      "purpose": "Non-Conflict Declaration",
      "current_quality_score": 0,
      "recommendations_ar": ["..."]
    }},
    "kyc": {{
      "purpose": "Know Your Customer",
      "current_quality_score": 0,
      "recommendations_ar": ["..."],
      "missing_critical_data_ar": ["..."]
    }},
    "ndu": {{
      "purpose": "Non-Disclosure Undertaking",
      "current_quality_score": 0,
      "recommendations_ar": ["..."]
    }}
  }},
  
  "action_plan_priority_ordered": [
    {{
      "step_number": 1,
      "action_ar": "أول خطوة",
      "deadline_days": 3,
      "owner_ar": "من المسؤول",
      "cost_estimate_aed": 0,
      "criticality": "CRITICAL | HIGH | MEDIUM | LOW"
    }}
  ],
  
  "final_pricing_recommendation": {{
    "rent_to_bid_aed_per_sqm": 0,
    "total_annual_rent_aed": 0,
    "revenue_share_pct": 0,
    "rationale_summary_ar": "ملخص استراتيجية التسعير"
  }}
}}

Be SPECIFIC with numbers. Use Abu Dhabi market knowledge. If unknown, estimate with reasoning."""


def build_advisor_md(advisor_result: dict, tender_intel: dict, bidder: dict) -> str:
    """Build the strategic advisory report in Arabic markdown."""
    
    auth = tender_intel.get("authority", {})
    project = tender_intel.get("project", {})
    company = bidder.get("company_legal_name", "[لم يُحدد]")
    
    exec_summary = advisor_result.get("executive_summary", {})
    financial = advisor_result.get("financial_strategy", {})
    technical = advisor_result.get("technical_strategy", {})
    legal = advisor_result.get("legal_strategy", {})
    market = advisor_result.get("market_intelligence", {})
    swot = advisor_result.get("bidder_swot", {})
    forms = advisor_result.get("per_form_recommendations", {})
    actions = advisor_result.get("action_plan_priority_ordered", [])
    pricing = advisor_result.get("final_pricing_recommendation", {})
    
    md = f"""# 🎯 التحليل الاستراتيجي للمناقصة

> **مستشار استراتيجي ذكي - مساندة للاستشارات الهندسية**  
> تاريخ التحليل: {datetime.now().strftime('%Y-%m-%d')}

---

## 📊 الملخص التنفيذي

| البند | القيمة |
|------|--------|
| **التوصية النهائية** | {exec_summary.get('decision_recommendation', '?')} |
| **درجة الجاذبية** | {exec_summary.get('attractiveness_score_out_of_10', 0)}/10 |
| **احتمالية الفوز** | {exec_summary.get('winning_probability_pct', 0)}% |
| **مستوى المنافسة المتوقع** | {exec_summary.get('expected_competition_level', '?')} |
| **عدد المنافسين المتوقع** | {exec_summary.get('estimated_competitors_count', 0)} |
| **الاستثمار الإجمالي الموصى به** | AED {exec_summary.get('recommended_total_investment_aed', 0):,} |

### 💡 لماذا التوصية؟
{exec_summary.get('decision_rationale_ar', '')}

---

## 💰 الاستراتيجية المالية

### 🎯 السعر الموصى به للتقديم

| البند | القيمة |
|------|--------|
| **الإيجار للحكومة (AED/م²)** | **AED {financial.get('recommended_rent_per_sqm_aed', 0):,}** |
| **نسبة الزيادة فوق الحد الأدنى** | {financial.get('rent_premium_over_floor_pct', 0)}% |
| **Revenue Share الموصى به** | {financial.get('recommended_revenue_share_pct', 0)}% |

**لماذا هذا السعر؟**  
{financial.get('rationale_for_rent_ar', '')}

**استراتيجية Revenue Share:**  
{financial.get('revenue_share_strategy_ar', '')}

### 📈 التوقعات المالية

| المؤشر | القيمة |
|--------|--------|
| الإيراد السنوي المتوقع | AED {financial.get('expected_annual_revenue_aed', 0):,} |
| CAPEX المتوقع | AED {financial.get('expected_capex_aed', 0):,} |
| OPEX السنوي | AED {financial.get('expected_opex_yearly_aed', 0):,} |
| **IRR (معدل العائد الداخلي)** | **{financial.get('projected_irr_pct', 0)}%** |
| **فترة الاسترداد** | **{financial.get('projected_payback_years', 0)} سنة** |
| سنة التعادل | السنة {financial.get('break_even_year', 0)} |

### 💼 توصية التمويل
{financial.get('financing_recommendation_ar', '')}

### ⚠️ المخاطر المالية الرئيسية
"""
    
    for risk in financial.get("key_financial_risks", []):
        md += f"- **{risk.get('risk_ar', '')}** | الأثر: AED {risk.get('impact_aed', 0):,}  \n"
        md += f"  - 🛡️ التخفيف: {risk.get('mitigation_ar', '')}\n"
    
    md += "\n---\n\n## 🏗️ الاستراتيجية الفنية\n\n"
    
    md += "### أولويات التصميم (مرتبة حسب الأهمية)\n\n"
    md += "| # | الأولوية | الوزن في التقييم | الاستثمار المطلوب |\n"
    md += "|---|---------|------------------|-------------------|\n"
    for i, priority in enumerate(technical.get("design_focus_priorities", []), 1):
        md += f"| {i} | {priority.get('priority_ar', '')} | {priority.get('evaluation_weight_pct', 0)}% | AED {priority.get('investment_required_aed', 0):,} |\n"
    
    md += f"\n### 🎨 المعماري الموصى به\n{technical.get('recommended_architect_profile_ar', '')}\n\n"
    
    md += "### ⭐ ميزات التصميم اللي لازم تركّز عليها\n"
    for feature in technical.get("key_design_features_to_emphasize_ar", []):
        md += f"- {feature}\n"
    
    md += "\n### 💵 ميزانية التصميم\n"
    md += f"- Concept Design: AED {technical.get('concept_design_budget_aed', 0):,}\n"
    md += f"- Master Plan: AED {technical.get('master_plan_budget_aed', 0):,}\n"
    md += f"- تكلفة البناء/م²: AED {technical.get('estimated_construction_cost_per_sqm_aed', 0):,}\n\n"
    
    md += f"### 🔧 استراتيجية التنفيذ\n{technical.get('construction_strategy_ar', '')}\n\n"
    
    md += "### 🌱 توصيات الاستدامة\n"
    for r in technical.get("sustainability_recommendations_ar", []):
        md += f"- {r}\n"
    
    md += "\n### ⚠️ المخاطر الفنية\n"
    for risk in technical.get("key_technical_risks", []):
        md += f"- **{risk.get('risk_ar', '')}**\n"
        md += f"  - 🛡️ {risk.get('mitigation_ar', '')}\n"
    
    md += "\n---\n\n## ⚖️ الاستراتيجية القانونية\n\n"
    md += f"**درجة المخاطر القانونية: {legal.get('legal_risks_score_out_of_10', 0)}/10**\n\n"
    
    md += "### 🚨 نقاط حمراء في عقد الإيجار طويل الأمد\n"
    for flag in legal.get("long_term_lease_red_flags_ar", []):
        md += f"- ⚠️ {flag}\n"
    
    md += "\n### 🤝 بنود قابلة للتفاوض\n"
    for clause in legal.get("negotiable_clauses_ar", []):
        md += f"- {clause}\n"
    
    md += "\n### 📋 الفجوات في الالتزام\n"
    for gap in legal.get("compliance_gaps_ar", []):
        md += f"- {gap}\n"
    
    md += "\n### ⚡ ترتيب أولويات المستندات القانونية\n"
    for i, doc in enumerate(legal.get("legal_documents_priority_order", []), 1):
        md += f"{i}. {doc}\n"
    
    md += f"\n💰 تكلفة الاستشارة القانونية المتوقعة: AED {legal.get('estimated_legal_consultation_cost_aed', 0):,}\n\n"
    
    md += "---\n\n## 🌍 ذكاء السوق\n\n"
    
    md += "### 📊 معدلات السوق الحالية (AED/م²/سنة)\n\n"
    market_rates = market.get("current_market_rent_per_sqm_aed", {})
    md += "| النوع | الحد الأدنى | الحد الأعلى |\n"
    md += "|------|-----------|-----------|\n"
    md += f"| محلات | AED {market_rates.get('shops_low', 0):,} | AED {market_rates.get('shops_high', 0):,} |\n"
    md += f"| ورش | AED {market_rates.get('workshops_low', 0):,} | AED {market_rates.get('workshops_high', 0):,} |\n"
    md += f"| مستودعات | AED {market_rates.get('warehouses_low', 0):,} | AED {market_rates.get('warehouses_high', 0):,} |\n"
    
    md += "\n### 🏆 المناقصات المشابهة السابقة\n\n"
    for comp in market.get("comparable_tender_winners", []):
        md += f"- **{comp.get('tender_name', '?')}** ({comp.get('year', '?')})\n"
        md += f"  - السعر الفائز: AED {comp.get('winning_bid_aed_per_sqm', 0):,}/م²\n"
        md += f"  - ملاحظات: {comp.get('notes_ar', '')}\n"
    
    md += f"\n### 📈 اتجاهات السوق\n{market.get('market_trends_ar', '')}\n\n"
    md += f"### 🎯 تحليل الطلب في المنطقة\n{market.get('demand_analysis_ar', '')}\n\n"
    md += f"### 🥊 تحليل المنافسين\n{market.get('competitor_analysis_ar', '')}\n\n"
    
    md += "---\n\n## 🎯 تحليل SWOT لشركتك\n\n"
    md += f"**درجة الجاهزية: {swot.get('bidder_readiness_score_out_of_10', 0)}/10**\n\n"
    
    md += "### ✅ نقاط القوة\n"
    for s in swot.get("strengths_ar", []):
        md += f"- {s}\n"
    
    md += "\n### ❌ نقاط الضعف\n"
    for w in swot.get("weaknesses_ar", []):
        md += f"- {w}\n"
    
    md += "\n### 🌟 الفرص\n"
    for o in swot.get("opportunities_ar", []):
        md += f"- {o}\n"
    
    md += "\n### ⚠️ التهديدات\n"
    for t in swot.get("threats_ar", []):
        md += f"- {t}\n"
    
    md += "\n---\n\n## 📝 توصيات على كل نموذج\n\n"
    
    form_labels = {
        "form_a": "📄 Form A - خطاب المناقصة",
        "form_b": "📊 Form B - الخبرة والقدرات",
        "form_h": "📋 Form H - إعلان عدم تضارب المصالح",
        "kyc": "👤 KYC Form - اعرف عميلك",
        "ndu": "🤐 NDU Form - تعهد عدم الإفصاح",
    }
    
    for form_key, form_label in form_labels.items():
        form_data = forms.get(form_key, {})
        if not form_data:
            continue
        md += f"### {form_label}\n"
        score = form_data.get("current_quality_score", 0)
        stars = "⭐" * int(score / 2) if score else ""
        md += f"**جودة النموذج الحالية: {score}/10 {stars}**\n\n"
        
        md += "**التوصيات:**\n"
        for rec in form_data.get("recommendations_ar", []):
            md += f"- {rec}\n"
        
        critical = form_data.get("critical_fields_ar", [])
        if critical:
            md += "\n**حقول حرجة لازم تركز عليها:**\n"
            for c in critical:
                md += f"- ⚡ {c}\n"
        
        missing = form_data.get("missing_critical_data_ar", [])
        if missing:
            md += "\n**بيانات ناقصة وضرورية:**\n"
            for m in missing:
                md += f"- 🚨 {m}\n"
        
        additional = form_data.get("additional_documents_to_attach_ar", [])
        if additional:
            md += "\n**مستندات إضافية لازم ترفقها:**\n"
            for a in additional:
                md += f"- 📎 {a}\n"
        
        md += "\n"
    
    md += "---\n\n## 🎬 خطة العمل (مرتبة حسب الأولوية)\n\n"
    md += "| # | الإجراء | المدة | المسؤول | التكلفة | الأهمية |\n"
    md += "|---|---------|------|---------|---------|--------|\n"
    
    for action in actions[:15]:
        crit = action.get("criticality", "MEDIUM")
        crit_emoji = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(crit, "⚪")
        md += f"| {action.get('step_number', '?')} | {action.get('action_ar', '')} | {action.get('deadline_days', 0)} يوم | {action.get('owner_ar', '')} | AED {action.get('cost_estimate_aed', 0):,} | {crit_emoji} {crit} |\n"
    
    md += f"\n---\n\n## 🎯 السعر النهائي الموصى به للتقديم\n\n"
    md += f"### 💎 توصية السعر النهائية\n\n"
    md += f"| البند | القيمة |\n"
    md += f"|------|--------|\n"
    md += f"| **الإيجار للحكومة** | **AED {pricing.get('rent_to_bid_aed_per_sqm', 0):,} / م² / سنة** |\n"
    md += f"| **إجمالي الإيجار السنوي** | **AED {pricing.get('total_annual_rent_aed', 0):,}** |\n"
    md += f"| **Revenue Share** | **{pricing.get('revenue_share_pct', 0)}%** |\n\n"
    md += f"### 📝 ملخص استراتيجية التسعير\n{pricing.get('rationale_summary_ar', '')}\n\n"
    
    md += "---\n\n"
    md += f"*تم توليد هذا التحليل بواسطة AI استراتيجي - منصة مساندة*  \n"
    md += f"*تاريخ التحليل: {datetime.now().strftime('%Y-%m-%d %H:%M')}*  \n"
    md += f"*هذا تحليل استراتيجي مبني على بيانات المناقصة وملف الشركة. التوصيات إرشادية وتحتاج مراجعة فريق متخصص.*\n"
    
    return md


def main():
    if len(sys.argv) != 4:
        print("Usage: strategic_advisor.py <tender_intel.json> <bidder_data.json> <output_md>")
        sys.exit(1)
    
    intel_path = Path(sys.argv[1])
    bidder_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    
    if not intel_path.exists():
        print(f"ERROR: intel file not found: {intel_path}", file=sys.stderr)
        sys.exit(1)
    
    intel = json.loads(intel_path.read_text(encoding="utf-8"))
    bidder = json.loads(bidder_path.read_text(encoding="utf-8"))
    
    print("╔══ Musanada Strategic AI Advisor ══╗")
    print(f"║ Tender: {intel.get('authority', {}).get('tender_title_en', '?')[:38]}")
    print(f"║ Bidder: {bidder.get('company_legal_name', '?')[:38]}")
    print(f"╚════════════════════════════════════╝\n")
    
    # Truncate JSON to fit in prompt (focus on key sections)
    intel_compact = {
        "authority": intel.get("authority", {}),
        "project": intel.get("project", {}),
        "schedule": intel.get("schedule", {}),
        "financial": intel.get("financial", {}),
        "evaluation": intel.get("evaluation", {}),
        "required_documents": intel.get("required_documents", {}),
        "eligibility": intel.get("eligibility", {}),
        "key_obligations": intel.get("key_obligations", {}),
    }
    
    bidder_compact = {
        "company_legal_name": bidder.get("company_legal_name"),
        "legal_form": bidder.get("legal_form"),
        "establishment_date": bidder.get("establishment_date"),
        "years_experience": bidder.get("years_experience"),
        "nature_of_business": bidder.get("nature_of_business"),
        "trade_license_no": bidder.get("trade_license_no"),
        "projects_count": len(bidder.get("projects_completed", [])),
        "projects_total_value_aed": sum(
            (p.get("amount", 0) or 0) for p in bidder.get("projects_completed", [])
            if isinstance(p.get("amount"), (int, float))
        ),
        "has_audited_financials": bool(bidder.get("_extracted_intel", {}).get("financials")),
        "has_company_profile": bool(bidder.get("_extracted_intel", {}).get("profile")),
        "projects_sample": bidder.get("projects_completed", [])[:5],
    }
    
    user_prompt = COMPREHENSIVE_ADVISOR_PROMPT.format(
        tender_intel=json.dumps(intel_compact, ensure_ascii=False, indent=2)[:18000],
        bidder_data=json.dumps(bidder_compact, ensure_ascii=False, indent=2)[:6000],
    )
    
    print("[1/2] Sending to GPT-4o for strategic analysis...")
    start = time.time()
    
    result = call_openai_with_search(api_key, ADVISOR_SYSTEM, user_prompt, model="gpt-4o")
    
    elapsed = time.time() - start
    print(f"[2/2] Done in {elapsed:.1f}s")
    
    if not result:
        print("ERROR: AI returned empty response", file=sys.stderr)
        sys.exit(1)
    
    # Save raw JSON for debugging
    json_path = output_path.with_suffix(".json")
    json_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Raw JSON: {json_path}")
    
    # Build Arabic markdown
    md = build_advisor_md(result, intel, bidder)
    output_path.write_text(md, encoding="utf-8")
    print(f"  Markdown: {output_path}")
    print(f"  Size: {output_path.stat().st_size // 1024} KB ({len(md.split(chr(10)))} lines)")
    
    # Summary
    summ = result.get("executive_summary", {})
    pricing = result.get("final_pricing_recommendation", {})
    print(f"\n  📊 Decision: {summ.get('decision_recommendation')}")
    print(f"  📊 Attractiveness: {summ.get('attractiveness_score_out_of_10')}/10")
    print(f"  📊 Win probability: {summ.get('winning_probability_pct')}%")
    print(f"  💎 Recommended rent: AED {pricing.get('rent_to_bid_aed_per_sqm', 0):,}/m² (+{pricing.get('revenue_share_pct', 0)}% rev share)")


if __name__ == "__main__":
    main()
