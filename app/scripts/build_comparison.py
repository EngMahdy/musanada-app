#!/usr/bin/env python3
"""
build_comparison.py — يبني جدول مقارنة بين كل المناقصات.

الاستخدام:
  python3 build_comparison.py <tender_workspace_dir> <output_md>
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import re


def days_until(date_str):
    try:
        clean = re.sub(r'(\d+)(?:st|nd|rd|th)', r'\1', date_str)
        for fmt in ["%d %B %Y", "%d %b %Y"]:
            try:
                d = datetime.strptime(clean.strip(), fmt)
                return (d - datetime.now()).days
            except:
                continue
    except:
        pass
    return None


def calc_attractiveness(meta):
    """يحسب درجة جاذبية مبدئية (1-5) بناء على المساحة والإيجار."""
    try:
        area = float(meta.get('land_area_sqm', '0').replace(',', ''))
        rent_sqm = float(meta.get('min_rent_per_sqm', '0').replace(',', ''))
        if area == 0 or rent_sqm == 0:
            return "—"
        
        # heuristic: لو المساحة كبيرة (>10000) والإيجار معقول (<150/sqm) = جذابة
        if area > 15000 and rent_sqm < 100:
            return "⭐⭐⭐⭐⭐"
        elif area > 10000 and rent_sqm < 120:
            return "⭐⭐⭐⭐"
        elif area > 5000:
            return "⭐⭐⭐"
        else:
            return "⭐⭐"
    except:
        return "—"


def main():
    if len(sys.argv) != 3:
        print("Usage: build_comparison.py <workspace_dir> <output_md>")
        sys.exit(1)
    
    workspace = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    
    tenders = []
    for td in sorted(workspace.iterdir()):
        if not td.is_dir():
            continue
        meta_path = td / "tender_meta.json"
        inv_path = td / "files_inventory.json"
        if not meta_path.exists():
            continue
        
        meta = json.loads(meta_path.read_text(encoding='utf-8'))
        inv = json.loads(inv_path.read_text(encoding='utf-8'))
        
        days = days_until(meta.get('closing_date', ''))
        days_str = f"{days} يوم" if days else "—"
        
        # احسب الإيجار السنوي
        try:
            area = float(meta.get('land_area_sqm', '0').replace(',', ''))
            rent_sqm = float(meta.get('min_rent_per_sqm', '0').replace(',', ''))
            min_annual = int(area * rent_sqm) if area and rent_sqm else 0
        except:
            min_annual = 0
        
        tenders.append({
            'name': inv['tender_name'],
            'facility': meta.get('facility_type', '-')[:40],
            'location': meta.get('location', '-')[:25],
            'area': meta.get('land_area_sqm', '-'),
            'rent_sqm': meta.get('min_rent_per_sqm', '-'),
            'annual_rent': f"{min_annual:,}" if min_annual else '-',
            'deadline': meta.get('closing_date', '-'),
            'days_left': days_str,
            'attractiveness': calc_attractiveness(meta),
            'has_forms': not bool(inv.get('missing', [])),
        })
    
    # رتّب حسب الأيام المتبقية ثم الجاذبية
    def sort_key(t):
        try:
            return int(t['days_left'].split()[0])
        except:
            return 999
    tenders.sort(key=sort_key)
    
    # ابني MD
    md = f"""# 📊 مقارنة المناقصات — DMT Abu Dhabi

> **عدد المناقصات:** {len(tenders)}  
> **تاريخ التحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## جدول المقارنة

| # | المناقصة | نوع المنشأة | الموقع | المساحة (م²) | إيجار/م² (AED) | إيجار سنوي (AED) | آخر موعد | المتبقي | جاذبية | النماذج |
|---|----------|------------|--------|--------------|----------------|------------------|----------|---------|--------|---------|
"""
    
    for i, t in enumerate(tenders, 1):
        forms_icon = "✅" if t['has_forms'] else "⚠️"
        md += f"| {i} | {t['name'][:50]} | {t['facility']} | {t['location']} | {t['area']} | {t['rent_sqm']} | {t['annual_rent']} | {t['deadline']} | {t['days_left']} | {t['attractiveness']} | {forms_icon} |\n"
    
    md += """
---

## مفتاح الرموز

- **النماذج:** ✅ = كل النماذج (Form A, B, H, KYC, NDU) متوفرة | ⚠️ = ملف RAR5 لم يُفك (سنستخدم نسخ موحّدة من مناقصة شقيقة)
- **الجاذبية:** ⭐⭐⭐⭐⭐ = مساحة كبيرة + إيجار منخفض | ⭐⭐ = صغيرة أو غالية

---

## تحليل سريع

"""
    
    # إحصائيات
    by_type = {}
    for t in tenders:
        ft = t['facility'][:30]
        by_type.setdefault(ft, []).append(t['name'])
    
    md += "### حسب نوع المنشأة\n\n"
    for ft, names in by_type.items():
        md += f"- **{ft}:** {len(names)} مناقصة\n"
    
    md += "\n### حسب الموقع\n\n"
    by_loc = {}
    for t in tenders:
        loc = t['location']
        by_loc.setdefault(loc, []).append(t['name'])
    for loc, names in by_loc.items():
        md += f"- **{loc}:** {len(names)} مناقصة\n"
    
    md += """

---

## توصيات الأولوية

### 🎯 ركّز على المناقصات اللي:
1. **متبقي 30+ يوم على Deadline** (وقت كافي للتحضير)
2. **جاذبية ⭐⭐⭐⭐ أو أكثر** (مساحة كبيرة + سعر معقول)
3. **في نوع منشأة تتطابق مع خبرتك**

### ⚠️ تجنّب المناقصات اللي:
1. **متبقي أقل من 20 يوم** (لو ما عندك Concept Design جاهز)
2. **في نوع منشأة جديد عليك** (تخسر نقاط Experience)
3. **في موقع بعيد عن عملياتك** (تكاليف لوجستية)

### 💡 اقتراح استراتيجي:
- **لا تقدّم لأكثر من 3-4 مناقصات في وقت واحد** — التركيز أهم من العدد
- استخدم نفس فريق الاستشاريين (معماري، مالي، قانوني) عبر كل المناقصات اللي اخترتها
- اعمل ICV Certificate **واحد** يخدم كل المناقصات
"""
    
    out_path.write_text(md, encoding='utf-8')
    print(f"[✓] Comparison matrix saved to {out_path}")


if __name__ == "__main__":
    main()
