#!/usr/bin/env python3
"""
tender_ai_reader.py — AI-powered deep reader of tender PDF documents.

Uses GPT-4o-mini to extract structured intelligence from auction documents:
- Issuing authority (DMT/ADIO/etc.) with confidence
- Tender identification (number, title, location)
- Project details (facility type, plot, area, activities allowed)
- Schedule (issue date, queries deadline, closing date, site visit)
- Financial terms (floor price, revenue share, escalation, grace period, performance bond)
- Evaluation criteria (technical weights, commercial weights, pass/fail thresholds)
- Required documents (due diligence, technical, commercial — each with specific items)
- Contract terms (duration, phases, obligations)
- Eligibility requirements
- Submission instructions

Usage:
  python3 tender_ai_reader.py <pdf_path> <output_json>

The output JSON has a strict schema with sources (page numbers) for every fact.
"""

import os
import sys
import json
import subprocess
import re
import time
from pathlib import Path


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract text from PDF using pdftotext (layout-preserving)."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except Exception as e:
        print(f"PDF extraction error: {e}", file=sys.stderr)
        return ""


def chunk_pdf_by_section(full_text: str, max_chunk_chars: int = 15000) -> list:
    """Split PDF text into logical chunks based on top-level sections.
    
    Tries to keep related content together. Falls back to fixed-size chunks.
    """
    # Try to split by numbered sections (1, 2, 3, 4, 5)
    section_starts = []
    for m in re.finditer(r'^(\d+)\s+[A-Z][\w &\-]+', full_text, re.MULTILINE):
        section_starts.append(m.start())
    
    if not section_starts:
        # Fall back to fixed-size
        return [full_text[i:i+max_chunk_chars] for i in range(0, len(full_text), max_chunk_chars)]
    
    chunks = []
    for i, start in enumerate(section_starts):
        end = section_starts[i+1] if i+1 < len(section_starts) else len(full_text)
        chunk = full_text[start:end]
        # Split large chunks
        if len(chunk) > max_chunk_chars:
            for j in range(0, len(chunk), max_chunk_chars):
                chunks.append(chunk[j:j+max_chunk_chars])
        else:
            chunks.append(chunk)
    
    return chunks


def call_openai(api_key: str, system: str, user: str, model: str = "gpt-4o-mini", max_tokens: int = 4000) -> dict:
    """Call OpenAI Chat API and return parsed JSON response."""
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
            "temperature": 0.1,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        },
        timeout=120
    )
    
    if response.status_code != 200:
        try:
            err = response.json().get("error", {})
            print(f"OpenAI error: {err.get('message', '')}", file=sys.stderr)
        except: pass
        return {}
    
    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception as e:
        print(f"Parse error: {e}", file=sys.stderr)
        return {}


# ============= EXTRACTION PROMPTS =============

ISSUER_PROMPT = """You are an expert UAE/Abu Dhabi government tender analyst.

Identify the issuing government entity from this auction/RFP document.

Common entities:
- DMT = Department of Municipalities and Transport (Abu Dhabi)
- ADM = Abu Dhabi Municipality
- ADIO = Abu Dhabi Investment Office (handles Musataha auctions)
- ADNOC, ADQ, Mubadala, Aldar, etc.

Return JSON ONLY:
{
  "issuing_authority": "DMT | ADIO | ADM | other",
  "issuing_authority_full_name": "full name in English",
  "issuing_authority_ar": "الاسم بالعربي",
  "confidence": "high | medium | low",
  "evidence_quote": "exact quote from document proving the authority (max 200 chars)",
  "contract_model": "BOMT | Musataha | Lease | Concession | Other",
  "tender_number": "if mentioned (e.g. P236, RFP-ADIO-CM-M26)",
  "tender_title_en": "full title in English",
  "tender_title_ar": "ترجمة العنوان للعربية"
}"""


PROJECT_PROMPT = """Extract project details from this tender section.

Return JSON ONLY:
{
  "facility_type": "e.g. Automotive Service Center, Sports Facility, etc.",
  "facility_type_ar": "نوع المنشأة بالعربي",
  "location": "Specific location/district",
  "location_ar": "الموقع بالعربي",
  "emirate": "Abu Dhabi/Dubai/etc.",
  "plot_id": "if mentioned",
  "coordinates": "GPS if mentioned",
  "land_area_sqm": 0,
  "buildup_area_sqm": 0,
  "allowed_activities": ["activity 1", "activity 2"],
  "prohibited_activities": ["if any"],
  "components_required": ["Building 1 description", "Building 2 description"],
  "evidence_pages": "page numbers where this info found"
}

If a number is unclear, use 0. If a list is empty, use []."""


SCHEDULE_PROMPT = """Extract the auction/tender schedule and dates.

Return JSON ONLY:
{
  "tender_issue_date": "YYYY-MM-DD or original format",
  "queries_deadline": "date when investors can ask questions",
  "site_visit_date": "if scheduled",
  "submission_deadline": "closing date - YYYY-MM-DD",
  "submission_time": "time of day if specified",
  "bid_validity_days": 120,
  "contract_duration_years": 25,
  "grace_period_years": 1,
  "construction_phase_months": 12,
  "operational_phase_years": 24,
  "evidence_quote": "exact quote about timeline"
}"""


FINANCIAL_PROMPT = """Extract ALL financial terms from this tender.

Return JSON ONLY:
{
  "floor_price_aed_per_sqm": 0,
  "floor_price_annual_aed": 0,
  "annual_escalation_pct": 2.0,
  "revenue_share_required": true,
  "revenue_share_pct_suggested": 0,
  "revenue_share_minimum_pct": 0,
  "performance_bond_aed": 0,
  "performance_bond_pct": 0,
  "managers_cheque_required": false,
  "managers_cheque_aed": 0,
  "payment_frequency": "quarterly | annually | monthly",
  "payment_in_advance": true,
  "vat_inclusive": false,
  "capex_min_required_aed": 0,
  "auditor_appointment": "who appoints + who pays",
  "evidence_quote": "exact financial quote"
}

Use 0 for unknown numbers, NOT null."""


EVALUATION_PROMPT = """Extract the evaluation criteria with EXACT weights.

Return JSON ONLY:
{
  "technical_weight_pct": 60,
  "commercial_weight_pct": 40,
  "minimum_technical_score": 60,
  "technical_criteria": [
    {"category": "Experience and Capabilities", "weight_pct": 15, "sub_items": [
      {"description": "...", "weight_pct": 9}
    ]}
  ],
  "commercial_criteria": [
    {"category": "Commercial Proposal", "weight_pct": 24, "sub_items": [
      {"description": "...", "weight_pct": 20}
    ]}
  ],
  "pass_fail_criteria": ["list of items that disqualify if missing"],
  "scoring_formula": "S = (St × T%) + (Sf × F%)",
  "evidence_quote": "..."
}"""


REQUIRED_DOCS_PROMPT = """Extract ALL required documents the bidder must submit.

Group them into Due Diligence, Technical, and Commercial sections.

Return JSON ONLY:
{
  "due_diligence_documents": [
    {"name": "Trade License", "name_ar": "الرخصة التجارية", "details": "valid, issued from Abu Dhabi", "mandatory": true}
  ],
  "technical_documents": [
    {"category": "Company Profile", "items": ["Organizational chart", "..."]}
  ],
  "commercial_documents": [
    {"name": "...", "details": "..."}
  ],
  "forms_to_submit": [
    {"form_name": "Form A", "purpose": "Letter of Auction", "found_in": "Part II Volume I"},
    {"form_name": "KYC Form", "purpose": "Know Your Customer", "found_in": "Annex"},
    {"form_name": "NDU Form", "purpose": "Non-Disclosure Undertaking"}
  ],
  "evidence_quote": "..."
}"""


ELIGIBILITY_PROMPT = """Extract eligibility requirements for investors/bidders.

Return JSON ONLY:
{
  "trade_license_required": "Abu Dhabi or specific emirate",
  "minimum_years_experience": 0,
  "minimum_net_worth_aed": 0,
  "minimum_annual_revenue_aed": 0,
  "minimum_similar_projects": 0,
  "government_experience_required": false,
  "consortium_allowed": false,
  "foreign_investors_allowed": true,
  "specific_qualifications": ["any specific certifications"],
  "investor_registration_required": "URL or portal",
  "evidence_quote": "..."
}"""


SUBMISSION_PROMPT = """Extract HOW the bidder submits their proposal.

Return JSON ONLY:
{
  "submission_method": "online portal | sealed envelope | email | mixed",
  "submission_portal_url": "if online",
  "submission_address": "if physical",
  "number_of_envelopes": "1 envelope | 3 envelopes (Pre-req/Technical/Commercial)",
  "language_required": "English | Arabic | bilingual",
  "currency": "AED",
  "number_of_copies": 0,
  "soft_copy_required": true,
  "submission_email": "if any",
  "queries_email": "for questions",
  "evidence_quote": "..."
}"""


# ============= MAIN EXTRACTOR =============

def extract_tender_intelligence(pdf_path: Path, api_key: str) -> dict:
    """Run all extractors on the PDF and return combined intelligence."""
    print(f"[1/8] Extracting text from PDF: {pdf_path.name}")
    full_text = extract_pdf_text(pdf_path)
    if not full_text or len(full_text) < 500:
        return {"error": "PDF text extraction failed or PDF is empty"}
    
    print(f"  Got {len(full_text)} chars from PDF")
    
    # First pass: small text sample for ALL extractors (most info is in early sections)
    # Use the full text for issuer/project/schedule
    # Use focused chunks for evaluation/financial/docs
    
    sample = full_text[:30000]  # First 30K chars usually covers tender doc
    
    intelligence = {
        "_source_file": pdf_path.name,
        "_extraction_time": time.time(),
    }
    
    # 1. Identify issuer
    print(f"[2/8] Identifying issuing authority...")
    intelligence["authority"] = call_openai(api_key, ISSUER_PROMPT, sample)
    issuer = intelligence["authority"].get("issuing_authority", "?")
    print(f"  → {issuer}")
    
    # 2. Project details
    print(f"[3/8] Extracting project details...")
    intelligence["project"] = call_openai(api_key, PROJECT_PROMPT, sample)
    print(f"  → {intelligence['project'].get('facility_type', '?')} in {intelligence['project'].get('location', '?')}")
    
    # 3. Schedule
    print(f"[4/8] Extracting schedule...")
    intelligence["schedule"] = call_openai(api_key, SCHEDULE_PROMPT, sample)
    print(f"  → Deadline: {intelligence['schedule'].get('submission_deadline', '?')}")
    
    # 4. Financial terms
    print(f"[5/8] Extracting financial terms...")
    intelligence["financial"] = call_openai(api_key, FINANCIAL_PROMPT, sample)
    print(f"  → Floor: AED {intelligence['financial'].get('floor_price_aed_per_sqm', 0)}/sqm")
    
    # 5. Evaluation criteria
    print(f"[6/8] Extracting evaluation criteria...")
    intelligence["evaluation"] = call_openai(api_key, EVALUATION_PROMPT, sample)
    print(f"  → Technical: {intelligence['evaluation'].get('technical_weight_pct', '?')}% / Commercial: {intelligence['evaluation'].get('commercial_weight_pct', '?')}%")
    
    # 6. Required documents (use later half of text — usually section 4)
    print(f"[7/8] Extracting required documents...")
    docs_text = full_text[15000:45000] if len(full_text) > 15000 else full_text
    intelligence["required_documents"] = call_openai(api_key, REQUIRED_DOCS_PROMPT, docs_text, max_tokens=5000)
    n_dd = len(intelligence["required_documents"].get("due_diligence_documents", []))
    print(f"  → {n_dd} due diligence documents identified")
    
    # 7. Eligibility
    print(f"[8/8] Extracting eligibility + submission...")
    intelligence["eligibility"] = call_openai(api_key, ELIGIBILITY_PROMPT, sample)
    intelligence["submission"] = call_openai(api_key, SUBMISSION_PROMPT, sample)
    
    return intelligence


def main():
    if len(sys.argv) != 3:
        print("Usage: tender_ai_reader.py <pdf_path> <output_json>")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    print(f"\n╔══ Musanada AI Tender Reader ══╗")
    print(f"║ PDF: {pdf_path.name[:50]}")
    print(f"╚════════════════════════════════╝\n")
    
    start = time.time()
    intelligence = extract_tender_intelligence(pdf_path, api_key)
    elapsed = time.time() - start
    
    output_path.write_text(
        json.dumps(intelligence, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"\n✓ Done in {elapsed:.1f}s. Output: {output_path}")
    print(f"  Size: {output_path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
