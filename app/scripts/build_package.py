#!/usr/bin/env python3
"""
build_package.py — يبني مجلد التسليم النهائي لمناقصة واحدة.

الاستخدام:
  python3 build_package.py <tender_extracted_dir> <output_package_dir>

المدخلات: مجلد المناقصة بعد ما extract_tender.py اشتغل عليه (فيه raw_text/ و originals/)
المخرجات: مجلد جاهز للتسليم بالهيكل النهائي
"""

import sys
import json
import shutil
from pathlib import Path
from datetime import datetime


README_TEMPLATE = """# {tender_name}

## دليل المجلد

هذا المجلد يحتوي على كل ما يلزم لتقديم مناقصة:
**{tender_name}**

### هيكل المجلد:

| المجلد | الوصف |
|--------|-------|
| `01_Analysis_AR.md` | تحليل تفصيلي بالعربي للمناقصة (الموقع، السعر، المدة، المتطلبات) |
| `02_Submission_Checklist.md` | قائمة مراجعة لكل المستندات المطلوبة |
| `03_Original_Documents/` | الملفات الأصلية من DMT كما هي |
| `04_Filled_Forms/` | النماذج المملوءة جزئياً (مراجعة + توقيع مطلوب) |
| `05_Required_Documents_To_Collect/` | قائمة بالمستندات الخارجية اللي لازم تجمعها |
| `06_Commercial_Proposal_Draft/` | مسودة الجزء التجاري |

### الخطوات التالية:

1. راجع `01_Analysis_AR.md` بالكامل وافهم متطلبات المناقصة
2. افتح `02_Submission_Checklist.md` وابدأ في تجميع المستندات
3. اقرأ النماذج في `04_Filled_Forms/` وأكمل الحقول الفارغة
4. وقّع واختم كل النماذج
5. جهّز العرض التجاري من `06_Commercial_Proposal_Draft/`
6. ارفع كل شي على بوابة DMT قبل **{deadline}**

---
تم التجهيز بواسطة Tender Agent — {timestamp}
"""


def build_package(tender_dir: Path, output_dir: Path):
    """ينسخ ويرتب الملفات في الهيكل النهائي."""
    inv_path = tender_dir / "files_inventory.json"
    if not inv_path.exists():
        print(f"ERROR: No files_inventory.json in {tender_dir}")
        return False
    
    inventory = json.loads(inv_path.read_text(encoding='utf-8'))
    tender_name = inventory["tender_name"]
    
    safe_name = "".join(c if c.isalnum() or c in "_-" else "_" for c in tender_name)[:80]
    pkg_dir = output_dir / f"{safe_name}_Submission_Package"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    
    # إنشاء المجلدات الفرعية
    (pkg_dir / "03_Original_Documents").mkdir(exist_ok=True)
    (pkg_dir / "04_Filled_Forms").mkdir(exist_ok=True)
    (pkg_dir / "05_Required_Documents_To_Collect").mkdir(exist_ok=True)
    (pkg_dir / "06_Commercial_Proposal_Draft").mkdir(exist_ok=True)
    
    # نسخ الأصول
    originals = tender_dir / "originals"
    if originals.exists():
        for f in originals.iterdir():
            shutil.copy2(f, pkg_dir / "03_Original_Documents" / f.name)
    
    # نسخ الـ analysis لو موجود
    analysis = tender_dir / "analysis_AR.md"
    if analysis.exists():
        shutil.copy2(analysis, pkg_dir / "01_Analysis_AR.md")
    
    # نسخ الـ checklist لو موجود
    checklist = tender_dir / "checklist.md"
    if checklist.exists():
        shutil.copy2(checklist, pkg_dir / "02_Submission_Checklist.md")
    
    # نسخ الـ filled forms لو موجودة
    filled = tender_dir / "filled_forms"
    if filled.exists():
        for f in filled.iterdir():
            shutil.copy2(f, pkg_dir / "04_Filled_Forms" / f.name)
    
    # README
    deadline = inventory.get("deadline", "(راجع وثيقة المناقصة)")
    readme = README_TEMPLATE.format(
        tender_name=tender_name,
        deadline=deadline,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    (pkg_dir / "00_README_AR.md").write_text(readme, encoding='utf-8')
    
    # ملف قائمة المستندات الخارجية
    external_docs = """# المستندات الخارجية المطلوبة (يجب جمعها من جهات أخرى)

## مستندات الشركة (إجبارية):

- [ ] **Trade License** ساري المفعول صادر من أبوظبي
- [ ] **Power of Attorney** للممثل المفوض (موثق)
- [ ] **Emirates ID** للممثل المفوض (صورة واضحة من الوجهين)
- [ ] **Emirates IDs** للتنفيذيين الرئيسيين
- [ ] **Organizational Chart** الهيكل التنظيمي
- [ ] **Audited Financial Statements** لآخر 3 سنوات (من مدقق حسابات معتمد)
- [ ] **Etihad Credit Bureau Report** (تقرير الاتحاد للمعلومات الائتمانية)
- [ ] **Judicial Clearance Certificate** من دائرة قضاء أبوظبي
  - يجب أن يكون مؤرخ خلال آخر 30 يوم
  - يجب أن يطابق اسم الشركة بالضبط زي اللي في الرخصة التجارية
  - يجب أن يؤكد عدم وجود أي قضايا مدنية، تجارية، جنائية، أو تنفيذية ضد الشركة

## مستندات إضافية (للأفراد فقط):

- [ ] إثبات الدخل السنوي (إقرار ضريبي / شهادة راتب)
- [ ] قائمة الأصول

## مستندات فنية:

- [ ] **Company Profile** (4 صفحات حد أقصى)
- [ ] **Project Portfolio** — لكل مشروع سابق:
  - صورة عن العقد
  - شهادة إتمام من العميل
  - صور المشروع
- [ ] **Concept Design** (3D renderings, mood boards, narrative)
- [ ] **Master Plan** drawings
- [ ] **Sustainability Strategy** document
- [ ] **HSE Policies** (Health, Safety, Environment)

## مستندات تجارية:

- [ ] **10-Year Business Plan** (وثيقة كاملة)
- [ ] **Financial Model** (Excel مع CAPEX, OPEX, Revenue projections)
- [ ] **ICV Certificate** (In-Country Value) من جهة معتمدة في الإمارات

## نصائح:

1. ابدأ بـ Judicial Clearance Certificate لأنه ياخد وقت ومدته 30 يوم بس
2. حدّث Etihad Credit Bureau Report قبل التقديم بأسبوع كحد أقصى
3. تأكد أن الـPower of Attorney يغطي الصلاحيات المطلوبة بالضبط (التوقيع على مزادات، تمثيل أمام DMT)
4. خلي Trade License سارية على الأقل 6 شهور بعد تاريخ التقديم
"""
    (pkg_dir / "05_Required_Documents_To_Collect" / "_README.md").write_text(external_docs, encoding='utf-8')
    
    # ملف الـ Commercial Proposal template
    commercial_template = """# مسودة العرض التجاري — {tender_name}

## 1. Fixed Annual Rent (الإيجار السنوي الثابت)

- الحد الأدنى المطلوب: AED [يُملأ من Auction Document]
- العرض المقدم: AED ____________ سنوياً
- نسبة التصاعد السنوي: 2% (حسب شروط DMT)
- Grace Period (سنة 1): بدون إيجار

## 2. Revenue Share (نسبة من الإيرادات)

- النسبة المقترحة: ____% من إجمالي الإيرادات
- آلية التقرير: ربع سنوي

## 3. Financial Strength (القوة المالية)

- صافي الثروة: AED ____________
- مصدر التمويل: ____________
- نسبة التمويل الذاتي: ____%

## 4. 10-Year Business Plan

(يحتاج ملف Excel منفصل - استخدم template في نفس المجلد)

## 5. ICV Certificate

- صادر من: ____________
- النسبة: ____%
- تاريخ الإصدار: ____________

## 6. Binding Commitment Letter

> نحن، [اسم الشركة]، نلتزم بالعرض التجاري المقدم لمدة 120 يوم من تاريخ Auction Deadline.
> 
> التوقيع: ____________
> التاريخ: ____________
""".format(tender_name=tender_name)
    (pkg_dir / "06_Commercial_Proposal_Draft" / "Commercial_Proposal_Draft.md").write_text(commercial_template, encoding='utf-8')
    
    print(f"[✓] Package built: {pkg_dir}")
    return True


def main():
    if len(sys.argv) != 3:
        print("Usage: build_package.py <tender_extracted_dir> <output_dir>")
        sys.exit(1)
    
    tender_dir = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    
    # لو في master inventory، اعمل package لكل مناقصة
    master = tender_dir / "MASTER_INVENTORY.json"
    if master.exists():
        # حلقة على كل مجلد فرعي
        for sub in tender_dir.iterdir():
            if sub.is_dir() and (sub / "files_inventory.json").exists():
                build_package(sub, output_dir)
    else:
        build_package(tender_dir, output_dir)


if __name__ == "__main__":
    main()
