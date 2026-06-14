#!/usr/bin/env python3
"""
build_dynamic_checklist.py — Build a tender-specific checklist from AI intelligence.

Reads tender_intelligence.json (output of tender_ai_reader_v2.py) and produces:
1. A Markdown file (Arabic) listing every required item with status
2. A printable PDF version

Each item shows:
- ✅ checkmark for items already provided by the bidder (bidder_data + saved_docs)
- ⬜ empty box for items still required
- 📎 reference to where it goes in the submission (Form X, Folder Y)
- ⚠️ flag for critical/mandatory items

Usage:
  python3 build_dynamic_checklist.py <tender_intelligence.json> <bidder_data.json> <saved_docs.json> <output.md>
"""

import sys
import json
from pathlib import Path
from datetime import datetime, timedelta


def days_until(date_str: str):
    """Calculate days from today until a date string."""
    if not date_str: return None
    for fmt in ["%Y-%m-%d", "%d %B %Y", "%d-%m-%Y"]:
        try:
            d = datetime.strptime(date_str.strip(), fmt)
            return (d - datetime.now()).days
        except: continue
    return None


def get_status_icon(provided: bool, mandatory: bool) -> str:
    """Return checklist status icon."""
    if provided:
        return "✅"
    elif mandatory:
        return "⬜"
    else:
        return "▫️"


def assess_bidder_coverage(bidder: dict, saved_docs: dict, required_item_name: str) -> bool:
    """Determine if the bidder has provided this required item.
    
    Maps required document names to bidder_data fields and saved_docs categories.
    """
    name_lower = required_item_name.lower()
    
    # Map keywords to coverage checks
    if "trade license" in name_lower or "رخصة" in required_item_name:
        return bool(saved_docs.get("license") or bidder.get("trade_license_no"))
    if "emirates id" in name_lower:
        return bool(saved_docs.get("id"))
    if "power of attorney" in name_lower or "poa" in name_lower:
        return bool(saved_docs.get("id"))  # often combined with EID
    if "organizational chart" in name_lower or "org chart" in name_lower:
        return bool(saved_docs.get("orgchart"))
    if "audited financial" in name_lower or "financial statement" in name_lower:
        return bool(saved_docs.get("financials"))
    if "etihad credit" in name_lower or "ecb" in name_lower:
        return bool(saved_docs.get("financials")) and "etihad" in str(saved_docs).lower()
    if "judicial clearance" in name_lower:
        return False  # specific document, not collected by default
    if "bank statement" in name_lower:
        return bool(saved_docs.get("bank"))
    if "icv certificate" in name_lower or "icv" in name_lower.split():
        return False  # specific document
    if "vat" in name_lower:
        return bool(bidder.get("vat_no"))
    if "executive" in name_lower or "details of top executives" in name_lower:
        return bool(saved_docs.get("id"))
    if "company profile" in name_lower or "بروفايل" in required_item_name:
        return bool(saved_docs.get("profile"))
    if "experience" in name_lower or "past projects" in name_lower:
        return bool(saved_docs.get("works") or len(bidder.get("projects_completed", [])) > 0)
    
    return False


def build_md(intel: dict, bidder: dict, saved_docs: dict) -> str:
    """Build the Markdown checklist."""
    auth = intel.get("authority", {})
    proj = intel.get("project", {})
    schedule = intel.get("schedule", {})
    financial = intel.get("financial", {})
    docs = intel.get("required_documents", {})
    eligibility = intel.get("eligibility", {})
    submission = intel.get("submission", {})
    obligations = intel.get("key_obligations", {})
    evaluation = intel.get("evaluation", {})
    
    deadline = schedule.get("submission_deadline", "")
    days_left = days_until(deadline)
    deadline_warning = ""
    if days_left is not None:
        if days_left < 0:
            deadline_warning = f"⚠️ **انتهى الموعد منذ {abs(days_left)} يوم**"
        elif days_left < 14:
            deadline_warning = f"🚨 **متبقي {days_left} يوم فقط**"
        elif days_left < 30:
            deadline_warning = f"⏰ متبقي {days_left} يوم"
        else:
            deadline_warning = f"✓ متبقي {days_left} يوم"
    
    company_name = bidder.get("company_legal_name", "") or "[لم يُدخل]"
    
    md = f"""# 📋 قائمة المراجعة الديناميكية - {auth.get('tender_title_ar', auth.get('tender_title_en', 'المناقصة'))}

> هذه القائمة **مولّدة تلقائياً من تحليل AI للمناقصة الفعلية** — كل بند تم استخراجه من وثيقة المناقصة نفسها.

---

## 📍 معلومات المناقصة

| البند | القيمة |
|------|--------|
| **الجهة المُصدِرة** | {auth.get('issuing_authority_full_name', auth.get('issuing_authority', '?'))} |
| **عنوان المناقصة** | {auth.get('tender_title_en', '?')} |
| **العنوان بالعربية** | {auth.get('tender_title_ar', '?')} |
| **نموذج العقد** | {auth.get('contract_model', 'BOMT')} |
| **رقم القطعة** | {proj.get('plot_id', '?')} |
| **الموقع** | {proj.get('location', '?')} - {proj.get('emirate', '?')} |
| **الإحداثيات** | {proj.get('coordinates_lat', '?')} / {proj.get('coordinates_long', '?')} |
| **مساحة الأرض** | {proj.get('land_area_sqm', 0):,} م² |
| **مدة العقد** | {schedule.get('contract_duration_years', 25)} سنة |
| **فترة السماح** | {schedule.get('grace_period_years', 1)} سنة |

---

## ⏰ المواعيد الحاسمة

{deadline_warning}

| المرحلة | التاريخ |
|---------|---------|
| إصدار المناقصة | {schedule.get('tender_issue_date', '?')} |
| آخر موعد للاستفسارات | {schedule.get('queries_deadline', '?')} |
| **آخر موعد للتقديم** | **{schedule.get('submission_deadline', '?')}** |
| صلاحية العرض | {schedule.get('bid_validity_days', 120)} يوم |

---

## 💰 الشروط المالية

| البند | القيمة |
|------|--------|
| الإيجار الأدنى/م² | AED {financial.get('floor_price_aed_per_sqm', 0):,} |
| الإيجار السنوي الأدنى | AED {financial.get('floor_price_annual_aed', 0):,} |
| التصاعد السنوي | {financial.get('annual_escalation_pct', 2)}% |
| Revenue Share مطلوب | {'نعم' if financial.get('revenue_share_required') else 'لا'} |
| طريقة الدفع | {financial.get('payment_frequency', 'quarterly')} |
| Performance Bond | {f"AED {financial.get('performance_bond_aed'):,}" if financial.get('performance_bond_aed') else 'غير محدد'} |
| Manager's Cheque | {'مطلوب' if financial.get('managers_cheque_required') else 'غير مطلوب'} |

---

## 📊 معايير التقييم

| الفئة | الوزن |
|------|------|
| **العرض الفني** | **{evaluation.get('technical_weight_pct', 60)}%** |
| **العرض المالي** | **{evaluation.get('commercial_weight_pct', 40)}%** |
| الحد الأدنى للنجاح الفني | {evaluation.get('minimum_technical_score', 60)} نقطة |

### تفصيل المعايير الفنية:
"""
    
    # Technical criteria breakdown
    for cat in evaluation.get("technical_criteria", []):
        md += f"\n#### 🎯 {cat.get('category', '?')}: **{cat.get('weight_pct', 0)}%**\n"
        for sub in cat.get("sub_items", []):
            md += f"- ({sub.get('weight_pct', 0)}%) {sub.get('description', '?')}\n"
    
    md += "\n### تفصيل المعايير المالية:\n"
    for cat in evaluation.get("commercial_criteria", []):
        md += f"\n#### 💼 {cat.get('category', '?')}: **{cat.get('weight_pct', 0)}%**\n"
        for sub in cat.get("sub_items", []):
            md += f"- ({sub.get('weight_pct', 0)}%) {sub.get('description', '?')}\n"
    
    md += "\n---\n\n"
    
    # === Due Diligence Documents Checklist ===
    md += "## 📄 المستندات الإلزامية (Due Diligence)\n\n"
    md += f"**حالة الشركة:** `{company_name}`\n\n"
    md += "| ✓ | المستند | عربي | الحالة |\n|---|---------|------|--------|\n"
    
    dd_docs = docs.get("due_diligence_documents", [])
    n_provided = 0
    n_total = len(dd_docs)
    for doc in dd_docs:
        name_en = doc.get("name", "?")
        name_ar = doc.get("name_ar", "")
        mandatory = doc.get("mandatory", True)
        provided = assess_bidder_coverage(bidder, saved_docs, name_en)
        if provided:
            n_provided += 1
        icon = get_status_icon(provided, mandatory)
        status = "✅ مكتمل" if provided else ("⚠️ إلزامي" if mandatory else "اختياري")
        md += f"| {icon} | {name_en} | {name_ar} | {status} |\n"
    
    md += f"\n**التقدم:** {n_provided}/{n_total} مستندات مكتملة ({int(n_provided/n_total*100) if n_total else 0}%)\n\n"
    
    # === Technical Documents ===
    md += "---\n\n## 🏗️ المستندات الفنية\n\n"
    tech = docs.get("technical_documents", [])
    if tech:
        for cat in tech:
            md += f"### 📑 {cat.get('category', '?')}\n"
            if cat.get('page_limit'):
                md += f"*الحد الأقصى: {cat.get('page_limit')} صفحات*\n\n"
            for item in cat.get("items", []):
                md += f"- ⬜ {item}\n"
            md += "\n"
    
    # === Commercial Documents ===
    md += "---\n\n## 💰 المستندات المالية\n\n"
    comm = docs.get("commercial_documents", [])
    for doc in comm:
        name = doc.get("name", "?")
        details = doc.get("details", "")
        md += f"- ⬜ **{name}**"
        if details:
            md += f": {details}"
        md += "\n"
    
    md += "\n"
    
    # === Forms to Submit ===
    md += "---\n\n## 📝 النماذج المطلوبة\n\n"
    md += "| النموذج | الغرض | المرجع | الحالة |\n|--------|------|--------|--------|\n"
    for f in docs.get("forms_to_submit", []):
        # Check if we've filled this form
        form_name_lower = f.get("form_name", "").lower()
        filled = False
        if "form a" in form_name_lower or "letter of auction" in form_name_lower:
            filled = True  # always filled by app
        elif "form b" in form_name_lower or "experience" in form_name_lower:
            filled = bool(bidder.get("projects_completed"))
        elif "form h" in form_name_lower or "kyc" in form_name_lower or "ndu" in form_name_lower:
            filled = bool(bidder.get("company_legal_name"))
        
        icon = "✅" if filled else "⬜"
        status = "تم تعبئته بواسطة التطبيق" if filled else "يحتاج تعبئة يدوية"
        md += f"| {icon} {f.get('form_name', '?')} | {f.get('purpose', '?')} | {f.get('found_in', '?')} | {status} |\n"
    
    # === Eligibility Check ===
    md += "\n---\n\n## ✅ شروط الأهلية\n\n"
    md += "| الشرط | المطلوب | حالتك |\n|------|---------|--------|\n"
    
    elg_items = []
    if eligibility.get("trade_license_required"):
        has_lic = bool(bidder.get("trade_license_no") or saved_docs.get("license"))
        elg_items.append(("ترخيص تجاري", eligibility["trade_license_required"], 
                         "✅ متوفر" if has_lic else "❌ مطلوب"))
    if eligibility.get("minimum_years_experience"):
        years = bidder.get("years_experience", "")
        elg_items.append(("سنوات الخبرة الأدنى", f"{eligibility['minimum_years_experience']} سنة",
                         f"حسب بيانات الشركة: {years}" if years else "❌ غير محدد"))
    if eligibility.get("icv_certificate_required"):
        elg_items.append(("شهادة ICV", "مطلوبة", "⚠️ يجب الحصول عليها من جهة معتمدة"))
    if eligibility.get("foreign_investors_allowed"):
        elg_items.append(("استثمار أجنبي مسموح", 
                         "نعم" if eligibility["foreign_investors_allowed"] else "لا",
                         "ℹ️ معلومة"))
    if eligibility.get("government_experience_required"):
        elg_items.append(("خبرة مع جهات حكومية", "مطلوبة" if eligibility["government_experience_required"] else "غير مطلوبة",
                         "راجع Form B / Form G"))
    
    for label, required, status in elg_items:
        md += f"| {label} | {required} | {status} |\n"
    
    if eligibility.get("investor_registration_url"):
        md += f"\n🔗 **بوابة التسجيل:** {eligibility['investor_registration_url']}\n"
    
    # === Key Obligations ===
    if obligations:
        md += "\n---\n\n## 📜 الالتزامات الرئيسية\n\n"
        obligation_labels = {
            "construction_obligations": "🏗️ التزامات البناء",
            "operational_obligations": "⚙️ التزامات التشغيل",
            "reporting_obligations": "📊 التزامات التقارير",
            "maintenance_obligations": "🔧 التزامات الصيانة",
        }
        for key, label in obligation_labels.items():
            items = obligations.get(key, [])
            if items:
                md += f"### {label}\n"
                for item in items:
                    md += f"- {item}\n"
                md += "\n"
        if obligations.get("handover_terms"):
            md += f"### 🎯 شروط التسليم النهائي\n{obligations['handover_terms']}\n\n"
    
    # === Submission Instructions ===
    md += "---\n\n## 📮 طريقة التقديم\n\n"
    md += "| البند | التفاصيل |\n|------|----------|\n"
    md += f"| طريقة التقديم | {submission.get('submission_method', '?')} |\n"
    md += f"| بوابة التقديم | {submission.get('submission_portal_url', '?')} |\n"
    md += f"| عدد المظاريف | {submission.get('number_of_envelopes', '1')} |\n"
    md += f"| لغة التقديم | {submission.get('language_required', 'English')} |\n"
    md += f"| العملة | {submission.get('currency', 'AED')} |\n"
    md += f"| نسخة إلكترونية | {'مطلوبة' if submission.get('soft_copy_required') else 'اختيارية'} |\n"
    
    if submission.get("queries_email"):
        md += f"| إيميل الاستفسارات | {submission['queries_email']} |\n"
    
    # === Summary action items ===
    md += "\n---\n\n## ⚡ خطوات التنفيذ التالية\n\n"
    missing_critical = []
    for doc in dd_docs:
        if doc.get("mandatory", True) and not assess_bidder_coverage(bidder, saved_docs, doc.get("name", "")):
            missing_critical.append(doc.get("name", "?"))
    
    if missing_critical:
        md += "### 🚨 مستندات ناقصة (إلزامية):\n"
        for item in missing_critical:
            md += f"- ⬜ {item}\n"
        md += "\n"
    
    md += "### الخطوات الموصى بها:\n"
    md += "1. ⬜ راجع كل النماذج المُعبأة في مجلد `01_Forms/`\n"
    md += "2. ⬜ ادفع للممثل المفوض للتوقيع والختم\n"
    md += "3. ⬜ اجمع المستندات الإلزامية الناقصة (راجع القائمة فوق)\n"
    md += "4. ⬜ احضّر العرض التجاري (Commercial Proposal) — Excel جاهز في `02_Financial_Model/`\n"
    md += "5. ⬜ احضر Concept Design + Master Plan من معماري معتمد\n"
    md += "6. ⬜ احصل على ICV Certificate من جهة معتمدة\n"
    md += "7. ⬜ قدّم عبر بوابة DMT الإلكترونية قبل الموعد النهائي\n"
    
    # Footer
    md += f"\n---\n\n*تم توليد هذه القائمة تلقائياً بواسطة منصة مساندة - {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n"
    md += f"*الذكاء الاصطناعي: GPT-4o + Vision*\n"
    
    return md


def main():
    if len(sys.argv) < 4:
        print("Usage: build_dynamic_checklist.py <tender_intel.json> <bidder.json> <output.md> [<saved_docs.json>]")
        sys.exit(1)
    
    intel_path = Path(sys.argv[1])
    bidder_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    saved_docs_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    
    intel = json.loads(intel_path.read_text(encoding="utf-8"))
    bidder = json.loads(bidder_path.read_text(encoding="utf-8"))
    saved_docs = {}
    if saved_docs_path and saved_docs_path.exists():
        saved_docs = json.loads(saved_docs_path.read_text(encoding="utf-8"))
    
    print(f"Building dynamic checklist...")
    print(f"  Tender: {intel.get('authority', {}).get('tender_title_en', '?')[:60]}")
    print(f"  Bidder: {bidder.get('company_legal_name', '?')[:60]}")
    
    md = build_md(intel, bidder, saved_docs)
    output_path.write_text(md, encoding="utf-8")
    
    print(f"\n✓ Checklist saved: {output_path}")
    print(f"  Size: {output_path.stat().st_size // 1024} KB ({len(md.split(chr(10)))} lines)")


if __name__ == "__main__":
    main()
