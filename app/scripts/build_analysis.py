#!/usr/bin/env python3
"""
build_analysis.py — يستخرج البيانات المهمة من Auction Document.pdf النصي،
ويبني analysis_AR.md لكل مناقصة.

الاستخدام:
  python3 build_analysis.py <tender_workspace_dir>

المخرجات: لكل مناقصة، يضيف:
  - analysis_AR.md
  - tender_meta.json (للاستخدام في fill_forms.py)
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime


def extract_field(text, patterns, default="غير محدد"):
    """يجرب عدة patterns ويرجع أول match."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).strip()
    return default


def parse_auction_document(text):
    """يستخرج البيانات الرئيسية من نص Auction Document."""
    meta = {}
    
    # عنوان المناقصة (السطر الثاني عادة)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    if len(lines) > 1:
        meta['auction_title'] = ' '.join(lines[:3]).replace('Auction Document', '').strip()
    
    # الموقع
    location_patterns = [
        r'Establishment of (?:an? )?[\w\s]+(?:in|at|,)\s+(Al [\w\s]+?)(?:,|\.|\n)',
        r'located in[\w\s]*?(Al [\w\s]+?)(?:,|\.|\n)',
        r'within (Al [\w\s]+?)(?:,|\.|\n)',
    ]
    meta['location'] = extract_field(text, location_patterns)
    
    # مساحة الأرض
    area_patterns = [
        r'total area of\s*([\d,\.]+)\s*square\s*meters',
        r'total area of\s*([\d,\.]+)\s*sqm',
        r'plot of land[\w\s]+?([\d,\.]+)\s*square\s*meters',
    ]
    meta['land_area_sqm'] = extract_field(text, area_patterns)
    
    # نوع المنشأة
    facility_patterns = [
        r'Establishment of (?:an?\s+)?([\w\s]+?)(?:in|,|\.|\n)',
    ]
    meta['facility_type'] = extract_field(text, facility_patterns)
    
    # مدة العقد
    duration_patterns = [
        r'lease contract for\s+(\d+)\s+years',
        r'total term of\s+\w+\s*\((\d+)\)\s+years',
        r'(\d+)\s+years?,?\s+inclusive of',
    ]
    meta['contract_years'] = extract_field(text, duration_patterns, "25")
    
    # الإيجار الأدنى لكل متر مربع
    rent_sqm_patterns = [
        r'AED\s+([\d,\.]+)\s*/\s*sqm',
        r'AED\s+([\d,\.]+)\s*per\s*sqm',
        r'minimum rental[\w\s]+?AED\s+([\d,\.]+)\s*/\s*sqm',
    ]
    meta['min_rent_per_sqm'] = extract_field(text, rent_sqm_patterns)
    
    # الإيجار السنوي الأدنى
    annual_rent_patterns = [
        r'(?:AED|~\s*AED)\s+([\d,]+)\s+per year',
        r'minimum fixed annual rent of[\w\s~]*?AED\s+([\d,]+)',
        r'fixed annual rent of[\w\s~]*?AED\s+([\d,]+)',
    ]
    meta['min_annual_rent_aed'] = extract_field(text, annual_rent_patterns)
    
    # تواريخ المناقصة
    tender_issue_patterns = [
        r'Tender Issue[\s\n]*([\d]{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})',
    ]
    meta['tender_issue_date'] = extract_field(text, tender_issue_patterns)
    
    queries_patterns = [
        r'Deadline to submit queries[\s\n]*([\d]{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})',
    ]
    meta['queries_deadline'] = extract_field(text, queries_patterns)
    
    closing_patterns = [
        r'Closing Date[\s\n]*([\d]{1,2}(?:st|nd|rd|th)?\s+\w+\s+\d{4})',
    ]
    meta['closing_date'] = extract_field(text, closing_patterns)
    
    # نسبة Revenue Share أو escalation
    escalation_patterns = [
        r'escalation of\s+([\d\.]+%)\s+every year',
        r'escalation\s+of\s+([\d\.]+%)',
    ]
    meta['annual_escalation'] = extract_field(text, escalation_patterns, "2%")
    
    # Grace period
    grace_patterns = [
        r'(\d+)[\s-]year[\s\w]*grace period',
        r'Grace Period[\s\(]+Year\s+(\d+)',
    ]
    meta['grace_period_years'] = extract_field(text, grace_patterns, "1")
    
    # الأنشطة المسموح بها (نأخذ section 2.2 بعد جدول المحتويات)
    # نبحث عن "2 Project Overview" كبداية حقيقية، ثم نأخذ ما بعد "Background and Objective"
    pov_start = text.find("2 Project Overview")
    if pov_start == -1:
        pov_start = text.find("Background and Objective")
    if pov_start > 0:
        chunk = text[pov_start:pov_start + 3000]
        bg_match = re.search(r'Background and Objective\s*([\s\S]+?)(?=2\.3|Project scope)', chunk)
        if bg_match:
            bg = bg_match.group(1)
            bullets = re.findall(r'(?:^|\n)\s*\d+\.\s+(.+?)(?=\n|$)', bg)
            meta['allowed_activities'] = [b.strip() for b in bullets if len(b.strip()) > 20][:6]
        else:
            meta['allowed_activities'] = []
    else:
        meta['allowed_activities'] = []
    
    return meta


def days_until(date_str):
    """يحسب الأيام المتبقية لتاريخ معين."""
    try:
        # نحاول parse "30th June 2026" format
        clean = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
        for fmt in ["%d %B %Y", "%d %b %Y", "%B %d, %Y", "%Y-%m-%d"]:
            try:
                d = datetime.strptime(clean.strip(), fmt)
                return (d - datetime.now()).days
            except:
                continue
    except:
        pass
    return None


def build_analysis_md(tender_dir: Path, template: str) -> str:
    """يبني analysis_AR.md من النص المستخرج."""
    auction_txt = tender_dir / "raw_text" / "auction_document.txt"
    if not auction_txt.exists():
        return None
    
    text = auction_txt.read_text(encoding='utf-8')
    meta = parse_auction_document(text)
    
    # احفظ meta كـ JSON للاستخدام في fill_forms
    (tender_dir / "tender_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    
    # احسب أيام للـdeadline
    days_left = days_until(meta.get('closing_date', ''))
    days_str = f"{days_left} يوم" if days_left else "غير محدد"
    
    # أنشطة كـmarkdown bullets
    activities_md = "\n".join(f"- {a}" for a in meta.get('allowed_activities', [])) or "- (راجع وثيقة المناقصة Section 2.2)"
    
    # ملخص تنفيذي
    inv = json.loads((tender_dir / "files_inventory.json").read_text(encoding='utf-8'))
    tender_name = inv["tender_name"]
    
    summary = f"""**{tender_name}** هي مناقصة من DMT أبوظبي لتأجير قطعة أرض بمساحة **{meta.get('land_area_sqm','?')} م²** في **{meta.get('location','?')}** لمدة **{meta.get('contract_years','25')} سنة** (شامل {meta.get('grace_period_years','1')} سنة Grace Period) بنظام Build-Operate-Maintain-Transfer.

- **الحد الأدنى للإيجار:** AED {meta.get('min_rent_per_sqm','?')}/م² (~AED {meta.get('min_annual_rent_aed','?')} سنوياً)
- **التصاعد السنوي:** {meta.get('annual_escalation','2%')}
- **آخر موعد للتقديم:** {meta.get('closing_date','غير محدد')} (**{days_str}** متبقي)
- **آخر موعد للأسئلة:** {meta.get('queries_deadline','غير محدد')}
"""
    
    # املأ template
    out = template.replace("{TENDER_NAME}", tender_name)
    out = out.replace("{AUCTION_NUMBER}", meta.get('auction_title', '-'))
    out = out.replace("{ISSUE_DATE}", meta.get('tender_issue_date', '-'))
    out = out.replace("{QUERIES_DEADLINE}", meta.get('queries_deadline', '-'))
    out = out.replace("{SUBMISSION_DEADLINE}", meta.get('closing_date', '-'))
    out = out.replace("{EXECUTIVE_SUMMARY}", summary)
    out = out.replace("{FACILITY_TYPE}", meta.get('facility_type', '-'))
    out = out.replace("{LOCATION}", meta.get('location', '-'))
    out = out.replace("{LAND_AREA}", meta.get('land_area_sqm', '-'))
    out = out.replace("{CONTRACT_DURATION}", f"{meta.get('contract_years','25')} سنة")
    out = out.replace("{CONSTRUCTION_PERIOD}", "18 شهر (6 تحضير + 12 بناء)")
    out = out.replace("{OPERATION_PERIOD}", "24 سنة")
    out = out.replace("{ALLOWED_ACTIVITIES}", activities_md)
    
    # تكاليف
    min_rent = meta.get('min_annual_rent_aed', '0').replace(',', '')
    try:
        rent_num = int(min_rent)
    except:
        rent_num = 0
    out = out.replace("{MIN_RENT_PER_SQM}", meta.get('min_rent_per_sqm', '-'))
    out = out.replace("{MIN_ANNUAL_RENT:,}", f"{rent_num:,}" if rent_num else "-")
    out = out.replace("{MIN_ANNUAL_RENT}", f"{rent_num:,}" if rent_num else "-")
    
    # CAPEX placeholders (تقديري — للمراجعة من المستخدم)
    try:
        area = int(meta.get('land_area_sqm', '0').replace(',', ''))
    except:
        area = 0
    capex_construction = area * 3500 if area else 0  # ~AED 3500/sqm كتقدير عام
    out = out.replace("{CAPEX_CONSTRUCTION}", f"AED {capex_construction:,} (تقديري)" if capex_construction else "-")
    out = out.replace("{CAPEX_EQUIPMENT}", "AED 2,000,000 (تقديري)")
    out = out.replace("{CAPEX_CONSULTING}", "AED 500,000 (تقديري)")
    out = out.replace("{CAPEX_WORKING_CAPITAL}", "AED 1,500,000 (تقديري)")
    total_capex = capex_construction + 2000000 + 500000 + 1500000
    out = out.replace("{CAPEX_TOTAL}", f"AED {total_capex:,} (تقديري - يحتاج دراسة)")
    
    # Documents (نضع نص افتراضي - سيعدّله المستخدم)
    out = out.replace("{DUE_DILIGENCE_DOCS}", "(راجع `02_Submission_Checklist.md` و `05_Required_Documents_To_Collect/_README.md`)")
    out = out.replace("{TECHNICAL_DOCS}", "Company Profile, Experience & Capabilities, Management Approach, Concept Design, Master Plan")
    out = out.replace("{COMMERCIAL_DOCS}", "Commercial Proposal, 10-Year Business Plan, Financial Model, ICV Certificate, Binding Letter")
    
    # توصيات
    recommendations = f"""بناءً على البيانات المتاحة:

1. **الجاذبية المالية:** المساحة {meta.get('land_area_sqm','?')} م² والإيجار AED {meta.get('min_rent_per_sqm','?')}/م² — قارن مع الإيرادات المتوقعة من النشاط ({meta.get('facility_type','المنشأة')}).

2. **الوقت المتبقي:** {days_str} — لو أقل من 30 يوم، الفرصة محدودة لتجهيز Concept Design و Master Plan احترافي.

3. **الموقع:** {meta.get('location','?')} — قيّم الديموغرافيا والمنافسة المحلية.

4. **التركيز على Facility Design (33% من التقييم):** استثمر في مكتب معماري معروف.

5. **ICV (16% من التقييم):** ابدأ مبكراً في إعداد ICV Certificate.
"""
    out = out.replace("{RECOMMENDATIONS}", recommendations)
    out = out.replace("{DAYS_TO_DEADLINE}", days_str)
    
    return out


def main():
    if len(sys.argv) != 2:
        print("Usage: build_analysis.py <tender_workspace_dir>")
        sys.exit(1)
    
    workspace = Path(sys.argv[1])
    # Look for templates in multiple locations
    here = Path(__file__).parent
    candidates = [
        here.parent / "templates_agent" / "analysis_template_AR.md",  # deploy structure
        here.parent / "templates" / "analysis_template_AR.md",         # original
        Path.home() / ".opencode" / "skills" / "tender-agent" / "templates" / "analysis_template_AR.md",
    ]
    template_path = next((p for p in candidates if p.exists()), candidates[0])
    template = template_path.read_text(encoding='utf-8')
    
    count = 0
    for tender_dir in workspace.iterdir():
        if not tender_dir.is_dir():
            continue
        if not (tender_dir / "files_inventory.json").exists():
            continue
        
        analysis = build_analysis_md(tender_dir, template)
        if analysis:
            (tender_dir / "analysis_AR.md").write_text(analysis, encoding='utf-8')
            print(f"  ✓ Analysis built: {tender_dir.name}")
            count += 1
    
    print(f"\n[✓] Built {count} analysis files.")


if __name__ == "__main__":
    main()
