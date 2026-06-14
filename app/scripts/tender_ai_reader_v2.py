#!/usr/bin/env python3
"""
tender_ai_reader_v2.py — Production deep tender reader.

Strategy:
- Pass 1 (FAST): GPT-4o-mini reads ALL chunks in parallel-like sequence — comprehensive but quick
- Pass 2 (REFINEMENT): GPT-4o reads the FULL text once for high-accuracy critical fields
- Pass 3 (VISION): GPT-4o Vision on appendix pages for Plot ID + coordinates + site plan

Target: 3-5 minutes per tender with high accuracy.

Usage:
  python3 tender_ai_reader_v2.py <pdf_path> <output_json> [--no-vision]
"""

import os
import sys
import json
import subprocess
import re
import time
import base64
from pathlib import Path


# ============= PDF EXTRACTION =============

def extract_pdf_text(pdf_path: Path) -> str:
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            capture_output=True, text=True, timeout=120
        )
        return result.stdout
    except Exception as e:
        print(f"PDF extract error: {e}", file=sys.stderr)
        return ""


def get_pdf_page_count(pdf_path: Path) -> int:
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True, text=True, timeout=30
        )
        for line in result.stdout.split("\n"):
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except Exception:
        pass
    return 0


def render_specific_pages(pdf_path: Path, output_dir: Path, page_numbers: list) -> list:
    """Render specific pages as PNG. Used for site plan / appendix vision."""
    output_dir.mkdir(parents=True, exist_ok=True)
    images = []
    for page in page_numbers:
        out_prefix = output_dir / f"page_{page:03d}"
        try:
            subprocess.run(
                ["pdftoppm", "-r", "120", "-f", str(page), "-l", str(page),
                 "-png", str(pdf_path), str(out_prefix)],
                capture_output=True, timeout=45
            )
            actual = output_dir / f"page_{page:03d}-1.png"
            if actual.exists():
                images.append(actual)
        except Exception as e:
            print(f"  Render page {page} failed: {e}", file=sys.stderr)
    return images


def chunk_text(text: str, chunk_size: int = 20000, overlap: int = 1500) -> list:
    """Chunk text trying to break at section boundaries.
    Guarantees forward progress (no infinite loops)."""
    if len(text) <= chunk_size:
        return [text]
    
    chunks = []
    pos = 0
    min_step = max(1000, chunk_size - overlap)  # ensure forward progress
    
    while pos < len(text):
        end = min(pos + chunk_size, len(text))
        
        # Try to align to a section boundary in last 400 chars
        if end < len(text):
            window_start = max(end - 400, pos + min_step)  # don't go behind min_step from pos
            if window_start < end:
                window = text[window_start:end]
                m = re.search(r'\n\d+(?:\.\d+)?\s+[A-Z]', window)
                if m:
                    end = window_start + m.start()
        
        chunks.append(text[pos:end])
        # Ensure we advance by at least min_step
        next_pos = max(pos + min_step, end - overlap)
        if next_pos <= pos:
            next_pos = pos + min_step
        pos = next_pos
    
    # Merge last tiny chunk into previous if it's < 5K chars (saves an API call)
    if len(chunks) >= 2 and len(chunks[-1]) < 5000:
        chunks[-2] = chunks[-2] + "\n\n" + chunks[-1]
        chunks.pop()
    
    return chunks


# ============= OPENAI HELPERS =============

def call_chat(api_key: str, system: str, user: str, model: str = "gpt-4o-mini", 
              max_tokens: int = 6000, timeout: int = 90) -> dict:
    """Single chat call returning parsed JSON."""
    import requests
    
    try:
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
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout
        )
        
        if response.status_code != 200:
            err = response.json().get("error", {}) if response.headers.get("content-type", "").startswith("application/json") else {}
            print(f"  ⚠ {model}: {err.get('message', response.text[:100])[:150]}", file=sys.stderr)
            return {}
        
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except requests.exceptions.Timeout:
        print(f"  ⚠ {model}: timeout after {timeout}s", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"  ⚠ {model} error: {e}", file=sys.stderr)
        return {}


def call_vision(api_key: str, system: str, prompt: str, image_paths: list,
                model: str = "gpt-4o-mini", timeout: int = 120) -> dict:
    """Vision API call."""
    import requests
    
    content = [{"type": "text", "text": prompt}]
    for p in image_paths[:3]:  # max 3 images
        try:
            with open(p, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{b64}", "detail": "high"}
            })
        except Exception:
            pass
    
    try:
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
                    {"role": "user", "content": content}
                ],
                "temperature": 0.0,
                "max_tokens": 3000,
                "response_format": {"type": "json_object"},
            },
            timeout=timeout
        )
        if response.status_code != 200:
            print(f"  ⚠ Vision: {response.text[:200]}", file=sys.stderr)
            return {}
        return json.loads(response.json()["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"  ⚠ Vision error: {e}", file=sys.stderr)
        return {}


# ============= MERGE LOGIC =============

def is_empty_value(v) -> bool:
    if v is None: return True
    if v == "": return True
    if v == 0: return True
    if v == []: return True
    if v == {}: return True
    if isinstance(v, str):
        return v.lower().strip() in ["not mentioned", "null", "n/a", "none", "tbd", "?", "not specified", "unknown"]
    return False


def deep_merge(base: dict, update: dict) -> dict:
    """Merge update into base. Replace empty values, keep richer values."""
    if not base:
        return update or {}
    if not update:
        return base
    
    for k, v in update.items():
        if k.startswith("_"):
            continue
        if k not in base:
            base[k] = v
        elif isinstance(v, dict) and isinstance(base[k], dict):
            base[k] = deep_merge(base[k], v)
        elif isinstance(v, list) and isinstance(base[k], list):
            # Keep longer list (more comprehensive)
            if len(v) > len(base[k]):
                base[k] = v
        elif is_empty_value(base[k]) and not is_empty_value(v):
            base[k] = v
    return base


# ============= PROMPTS =============

SYSTEM = """You are an EXPERT UAE/Abu Dhabi government procurement analyst with 20+ years of experience reading DMT, ADIO, ADM, ADNOC, and Mubadala tenders.

Rules:
1. NEVER hallucinate. If a value isn't in the text, use null, empty string, or 0
2. Numbers must be actual numbers (NOT "AED 552,828" → use 552828)
3. Dates in YYYY-MM-DD when possible
4. Return ONLY valid JSON matching the schema
5. Arabic for *_ar fields, English otherwise"""


EXTRACTION_SCHEMA = """{
  "authority": {
    "issuing_authority": "DMT | ADIO | ADM | ADNOC | Mubadala | Aldar | other",
    "issuing_authority_full_name": "...",
    "issuing_authority_ar": "...",
    "confidence": "high | medium | low",
    "evidence_quote": "exact quote (max 200 chars)",
    "contract_model": "BOMT | Musataha | Lease | Concession | Other",
    "tender_number": "e.g. P236, S14, RFP-ADIO-CM-M26",
    "tender_title_en": "...",
    "tender_title_ar": "...",
    "tender_reference": "any other reference IDs"
  },
  "project": {
    "facility_type": "...",
    "facility_type_ar": "...",
    "location": "specific district/area",
    "location_ar": "...",
    "emirate": "Abu Dhabi | Dubai | etc.",
    "plot_id": "exact plot reference e.g. AL SHAHAMAH NEW_P236",
    "plot_reference_full": "Municipality + District + Plot",
    "coordinates_lat": "e.g. 24°32'52.5\\"N",
    "coordinates_long": "e.g. 54°41'14.3\\"E",
    "land_area_sqm": 0,
    "buildup_area_sqm": 0,
    "max_building_height_m": 0,
    "max_floors": 0,
    "FAR_ratio": 0,
    "allowed_activities": ["..."],
    "prohibited_activities": ["..."],
    "components_required": [{"name": "...", "area_sqm": 0, "description": "..."}],
    "min_parking_spaces": 0
  },
  "schedule": {
    "tender_issue_date": "YYYY-MM-DD",
    "queries_deadline": "YYYY-MM-DD",
    "site_visit_date": null,
    "submission_deadline": "YYYY-MM-DD",
    "submission_time": "HH:MM",
    "bid_validity_days": 120,
    "permit_obtaining_months": 6,
    "construction_phase_months": 12,
    "operational_phase_years": 24,
    "contract_duration_years": 25,
    "grace_period_years": 1
  },
  "financial": {
    "floor_price_aed_per_sqm": 0,
    "floor_price_annual_aed": 0,
    "annual_escalation_pct": 2.0,
    "revenue_share_required": true,
    "revenue_share_pct_minimum": 0,
    "revenue_share_pct_suggested": 0,
    "performance_bond_aed": 0,
    "performance_bond_pct": 0,
    "performance_bond_validity_months": 0,
    "tender_bond_aed": 0,
    "managers_cheque_required": false,
    "managers_cheque_aed": 0,
    "payment_frequency": "quarterly",
    "payment_in_advance": true,
    "vat_inclusive": false,
    "capex_min_required_aed": 0,
    "auditor_appointed_by": "DMT | Bidder | Mutual",
    "auditor_cost_paid_by": "..."
  },
  "evaluation": {
    "technical_weight_pct": 60,
    "commercial_weight_pct": 40,
    "minimum_technical_score": 60,
    "pass_fail_only_items": ["e.g. financial strength"],
    "technical_criteria": [
      {"category": "...", "weight_pct": 0, "sub_items": [{"description": "...", "weight_pct": 0}]}
    ],
    "commercial_criteria": [
      {"category": "...", "weight_pct": 0, "sub_items": [{"description": "...", "weight_pct": 0}]}
    ],
    "scoring_formula": "S = (St × T%) + (Sf × F%)",
    "tie_breaker_rule": "if applicable"
  },
  "required_documents": {
    "due_diligence_documents": [
      {"name": "...", "name_ar": "...", "details": "...", "mandatory": true, "form_reference": "if any"}
    ],
    "technical_documents": [
      {"category": "Company Profile", "items": ["..."], "page_limit": 4}
    ],
    "commercial_documents": [
      {"name": "...", "details": "..."}
    ],
    "forms_to_submit": [
      {"form_name": "Form A", "purpose": "Letter of Auction", "found_in": "..."}
    ],
    "submission_volumes": ["Volume I Technical", "Volume II Commercial"]
  },
  "eligibility": {
    "trade_license_required": "...",
    "minimum_years_experience": 0,
    "minimum_net_worth_aed": 0,
    "minimum_annual_revenue_aed": 0,
    "minimum_similar_projects": 0,
    "government_experience_required": false,
    "consortium_allowed": false,
    "foreign_investors_allowed": true,
    "specific_qualifications": ["..."],
    "investor_registration_url": "...",
    "icv_certificate_required": false,
    "icv_minimum_pct": 0
  },
  "submission": {
    "submission_method": "online portal | sealed envelope | email",
    "submission_portal_url": "...",
    "submission_address": "...",
    "number_of_envelopes": "1 | 3",
    "language_required": "English | Arabic | bilingual",
    "currency": "AED",
    "number_of_copies": 0,
    "soft_copy_required": true,
    "queries_email": "..."
  },
  "key_obligations": {
    "construction_obligations": ["..."],
    "operational_obligations": ["..."],
    "reporting_obligations": ["..."],
    "maintenance_obligations": ["..."],
    "handover_terms": "..."
  },
  "regulatory_compliance": {
    "applicable_codes": ["DCR Appendix C", "UAE Accessibility Code"],
    "permits_required": ["..."],
    "sustainability_requirements": ["LEED | Estidama"],
    "safety_requirements": ["..."]
  }
}"""


def build_prompt(chunk_text: str, chunk_num: int, total_chunks: int) -> str:
    return f"""Extract structured tender data from this document chunk ({chunk_num}/{total_chunks}).

Return JSON matching this schema:
{EXTRACTION_SCHEMA}

Document chunk:
\"\"\"
{chunk_text}
\"\"\"

Return ONLY valid JSON. No explanations. Use null/0/[] for missing values."""


VISION_PROMPT = """These are pages from a tender document showing site plans, maps, location details, or appendices.

Extract ALL visible:
- Plot reference / Plot ID (e.g. "AL SHAHAMAH NEW_P236")
- Coordinates (lat/long, e.g. "24°32'52.5\\"N")
- Municipality / District
- Plot dimensions or area numbers
- Building zones and their areas
- Adjacent roads / boundaries
- Access points (entrances, exits)
- Scale (e.g. 1:1000)
- Any other table data visible

Return JSON:
{
  "plot_id": "extracted plot reference",
  "municipality": "...",
  "district": "...",
  "coordinates_lat": "with degrees/minutes/seconds notation",
  "coordinates_long": "...",
  "plot_dimensions": {"length_m": 0, "width_m": 0, "area_sqm": 0},
  "zones_visible": [{"name": "...", "area_sqm": 0}],
  "access_points": ["..."],
  "scale": "...",
  "additional_data": "any tabular data extracted"
}"""


# ============= MAIN EXTRACTION =============

def extract_deep(pdf_path: Path, api_key: str, use_vision: bool = True) -> dict:
    print(f"╔══ Musanada Deep Tender Reader v2 ══╗")
    print(f"║ PDF: {pdf_path.name[:38]}")
    print(f"╚════════════════════════════════════╝")
    start = time.time()
    
    # 1. Extract full text
    print("\n[1] Reading full PDF text...")
    full_text = extract_pdf_text(pdf_path)
    if not full_text or len(full_text) < 500:
        return {"error": "PDF text extraction failed"}
    
    page_count = get_pdf_page_count(pdf_path)
    print(f"    → {len(full_text):,} chars, {page_count} pages")
    
    # 2. Chunk the text
    chunks = chunk_text(full_text, chunk_size=20000, overlap=1500)
    print(f"\n[2] Split into {len(chunks)} chunks")
    
    # 3. Pass 1: gpt-4o-mini on each chunk (fast comprehensive coverage)
    aggregated = {
        "_source_file": pdf_path.name,
        "_total_pages": page_count,
        "_total_chars": len(full_text),
        "_chunks_count": len(chunks),
        "_model_primary": "gpt-4o-mini",
        "_model_refinement": "gpt-4o",
        "_vision_used": use_vision,
        "_started_at": time.time(),
    }
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n[3.{i}/{len(chunks)}] gpt-4o-mini reading chunk ({len(chunk):,} chars)...")
        prompt = build_prompt(chunk, i, len(chunks))
        result = call_chat(api_key, SYSTEM, prompt, model="gpt-4o-mini", max_tokens=8000, timeout=120)
        if result:
            aggregated = deep_merge(aggregated, result)
            print(f"    ✓ Authority: {aggregated.get('authority', {}).get('issuing_authority', '?')} | Plot: {aggregated.get('project', {}).get('plot_id', '?')}")
        else:
            print(f"    ✗ Empty result")
    
    # 4. Pass 2: gpt-4o refinement on FIRST 25K chars (most important)
    # This catches anything the mini missed, especially evaluation criteria details
    print(f"\n[4] gpt-4o refinement on critical first section...")
    refinement_text = full_text[:25000]
    refine_prompt = build_prompt(refinement_text, 1, 1)
    refined = call_chat(api_key, SYSTEM, refine_prompt, model="gpt-4o", max_tokens=10000, timeout=180)
    if refined:
        # Refined values OVERRIDE mini's when richer
        aggregated = deep_merge(aggregated, refined)
        print(f"    ✓ Refined. Final authority confidence: {aggregated.get('authority', {}).get('confidence', '?')}")
    
    # 5. Pass 3: Vision on appendix pages for plot details
    if use_vision and page_count > 3:
        print(f"\n[5] Vision pass on appendix pages (site plan / location)...")
        try:
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                # Target: last 3 pages (likely Appendix A: Location, Appendix B: Site Plan)
                target_pages = list(range(max(1, page_count - 4), page_count))
                images = render_specific_pages(pdf_path, tmpdir_path, target_pages)
                
                if images:
                    print(f"    Rendered {len(images)} appendix pages")
                    vision_result = call_vision(api_key, SYSTEM, VISION_PROMPT, images,
                                                model="gpt-4o-mini", timeout=120)
                    if vision_result:
                        aggregated["vision_findings"] = vision_result
                        # Merge into project section if those fields are empty
                        proj = aggregated.setdefault("project", {})
                        for field, vfield in [
                            ("plot_id", "plot_id"),
                            ("coordinates_lat", "coordinates_lat"),
                            ("coordinates_long", "coordinates_long"),
                        ]:
                            if is_empty_value(proj.get(field)) and not is_empty_value(vision_result.get(vfield)):
                                proj[field] = vision_result[vfield]
                                print(f"    ↳ Vision filled: {field} = {vision_result[vfield]}")
        except Exception as e:
            print(f"    ⚠ Vision skipped: {e}")
    
    elapsed = time.time() - start
    aggregated["_processing_seconds"] = round(elapsed, 1)
    aggregated["_finished_at"] = time.time()
    
    print(f"\n✓ Done in {elapsed:.1f}s ({elapsed/60:.1f}min)")
    return aggregated


def main():
    if len(sys.argv) < 3:
        print("Usage: tender_ai_reader_v2.py <pdf_path> <output_json> [--no-vision]")
        sys.exit(1)
    
    pdf_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    use_vision = "--no-vision" not in sys.argv
    
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY not set", file=sys.stderr)
        sys.exit(1)
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)
    
    intel = extract_deep(pdf_path, api_key, use_vision=use_vision)
    output_path.write_text(json.dumps(intel, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"\n✓ Saved: {output_path} ({output_path.stat().st_size // 1024} KB)")
    
    # Quick summary
    auth = intel.get("authority", {})
    proj = intel.get("project", {})
    print(f"\n  Authority: {auth.get('issuing_authority', '?')}")
    print(f"  Project: {proj.get('facility_type', '?')} in {proj.get('location', '?')}")
    print(f"  Plot ID: {proj.get('plot_id', '?')}")
    print(f"  Area: {proj.get('land_area_sqm', 0)} sqm")
    print(f"  Coordinates: {proj.get('coordinates_lat', '?')} / {proj.get('coordinates_long', '?')}")


if __name__ == "__main__":
    main()
