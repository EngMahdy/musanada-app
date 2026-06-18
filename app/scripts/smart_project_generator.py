#!/usr/bin/env python3
"""
🧠 Smart Project Generator
==========================
يولّد مشاريع سابقة **منطقية ومناسبة** للمناقصة:
- يحلل نوع المناقصة (مقاولات، أسواق، طرق، لاند سكيب...)
- يولّد 5-7 مشاريع سابقة بأسماء وتواريخ ومساحات واقعية
- يحرص على ألا يبدو "مفتعل"

Usage:
    python3 smart_project_generator.py <tender_meta.json> <company_name> <output.json>
"""

import json
import sys
import random
from pathlib import Path
from datetime import datetime, timedelta


# ===== Sector-Based Project Templates =====
SECTOR_TEMPLATES = {
    "contracting": {
        "name_ar": "مقاولات إنشائية",
        "projects": [
            ("مجمع سكني تجاري في {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مبنى", "{year}"),
            ("مبنى إداري متعدد الطوابق - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² GFA", "{year}"),
            ("فيلتين سكنيتين فاخرتين - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مساحة بناء", "{year}"),
            ("مستودع تجاري - منطقة المصافح الصناعية", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مبنى", "{year}"),
            ("توسعة مدرسة خاصة - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² إضافة", "{year}"),
            ("مبنى إداري لشركة استشارات", "AED {cost:,.0f}", "{area_sqm:,.0f} م² GFA", "{year}"),
            ("ترميم وتجديد فندق في الكورنيش", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ترميم", "{year}"),
        ],
        "cost_range": (3_000_000, 25_000_000),
        "area_range": (800, 6_000),
    },
    "markets_retail": {
        "name_ar": "مراكز تجارية وأسواق",
        "projects": [
            ("سوق شعبي تراثي - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² محلات", "{year}"),
            ("مجمع تجاري متعدد الاستخدامات - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² GLA", "{year}"),
            ("مركز خدمات صغير (Mini Mall) - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² تجاري", "{year}"),
            ("معرض سيارات - منطقة المصافح", "AED {cost:,.0f}", "{area_sqm:,.0f} م² Showroom", "{year}"),
            ("مطاعم شعبية متجمعة - منطقة الكورنيش", "AED {cost:,.0f}", "{area_sqm:,.0f} م² F&B", "{year}"),
            ("سوق خضار وفواكه نموذجي - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² سوق", "{year}"),
        ],
        "cost_range": (2_500_000, 18_000_000),
        "area_range": (600, 4_500),
    },
    "roads_infrastructure": {
        "name_ar": "طرق وبنية تحتية",
        "projects": [
            ("توسعة شارع {area} - 4 حارات", "AED {cost:,.0f}", "{area_sqm:,.0f} متر طولي", "{year}"),
            ("تنفيذ شبكة أمطار - منطقة {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² تغطية", "{year}"),
            ("ترميم وإعادة تأهيل طرق داخلية - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² رصف", "{year}"),
            ("إنشاء جسر مشاة - شارع المطار", "AED {cost:,.0f}", "{area_sqm:,.0f} م طول", "{year}"),
            ("تطوير تقاطعات وإشارات مرورية - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} تقاطعات", "{year}"),
            ("شبكة صرف صحي - حي {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م طولي", "{year}"),
        ],
        "cost_range": (5_000_000, 40_000_000),
        "area_range": (1_500, 12_000),
    },
    "landscape": {
        "name_ar": "أعمال لاند سكيب",
        "projects": [
            ("حديقة عامة كبرى - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مساحة خضراء", "{year}"),
            ("لاند سكيب فيلا فاخرة - السعديات", "AED {cost:,.0f}", "{area_sqm:,.0f} م² حدائق", "{year}"),
            ("ممشى ساحلي - الكورنيش", "AED {cost:,.0f}", "{area_sqm:,.0f} م طول ممشى", "{year}"),
            ("ميدان عام مع نوافير - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ميدان", "{year}"),
            ("حديقة أطفال نموذجية - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ألعاب", "{year}"),
            ("تشجير جانبي لشارع رئيسي", "AED {cost:,.0f}", "{area_sqm:,.0f} م خط زراعة", "{year}"),
            ("منطقة استراحة سياحية - شارع المطار", "AED {cost:,.0f}", "{area_sqm:,.0f} م² Rest Area", "{year}"),
        ],
        "cost_range": (800_000, 8_000_000),
        "area_range": (1_500, 25_000),
    },
    "automotive": {
        "name_ar": "خدمات سيارات",
        "projects": [
            ("مركز خدمة سيارات متكامل - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ورش", "{year}"),
            ("معرض سيارات + مغسلة - منطقة المصافح", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مبنى", "{year}"),
            ("محطة وقود + ميني ماركت - شارع المطار", "AED {cost:,.0f}", "{area_sqm:,.0f} م² محطة", "{year}"),
            ("مركز فحص فني للسيارات - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م² فحص", "{year}"),
            ("ورشة تصليح سيارات حديثة - منطقة الشاحنات", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ورشة", "{year}"),
        ],
        "cost_range": (1_500_000, 12_000_000),
        "area_range": (600, 3_500),
    },
    "industrial": {
        "name_ar": "مشاريع صناعية",
        "projects": [
            ("مصنع تعبئة مواد غذائية - مصفح الصناعية", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مصنع", "{year}"),
            ("مستودع لوجستي مبرّد - الوثبة", "AED {cost:,.0f}", "{area_sqm:,.0f} م² تبريد", "{year}"),
            ("ورشة تصنيع منتجات معدنية - ICAD", "AED {cost:,.0f}", "{area_sqm:,.0f} م² ورشة", "{year}"),
            ("مستودع توزيع تجاري - منطقة الموانئ", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مستودع", "{year}"),
            ("مصنع طوب ومواد بناء - الشهامة", "AED {cost:,.0f}", "{area_sqm:,.0f} م² مصنع", "{year}"),
        ],
        "cost_range": (4_000_000, 22_000_000),
        "area_range": (1_200, 6_500),
    },
    "general": {
        "name_ar": "مشاريع متنوعة",
        "projects": [
            ("مشروع تجاري متعدد الاستخدامات - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م²", "{year}"),
            ("مبنى خدمات حكومية - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م²", "{year}"),
            ("مركز مجتمعي - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م²", "{year}"),
            ("مشروع تطوير عقاري - {area}", "AED {cost:,.0f}", "{area_sqm:,.0f} م²", "{year}"),
        ],
        "cost_range": (2_000_000, 15_000_000),
        "area_range": (1_000, 5_000),
    },
}


# Areas in Abu Dhabi for realistic project locations
ABU_DHABI_AREAS = [
    "الشهامة", "الوثبة", "الفلاح", "خليفة سيتي", "الراحة",
    "الريم", "ياس", "صير بني ياس", "المرفأ", "المصفح",
    "بني ياس", "حليوة", "ICAD", "الكورنيش", "المنهل",
    "المشرف", "العين", "الذيد", "غياثي", "دلما"
]


def detect_project_type(tender_text: str) -> str:
    """كشف نوع المشروع من نص المناقصة"""
    t = tender_text.lower()
    
    # Score each type
    scores = {
        "contracting": 0,
        "markets_retail": 0,
        "roads_infrastructure": 0,
        "landscape": 0,
        "automotive": 0,
        "industrial": 0,
    }
    
    # Keywords (Arabic + English)
    keywords = {
        "contracting": ["مقاولات", "construction", "building", "إنشاء", "بناء", "مبنى", "تشييد"],
        "markets_retail": ["سوق", "market", "mall", "تجاري", "retail", "commercial", "محلات", "shops"],
        "roads_infrastructure": ["طرق", "roads", "infrastructure", "بنية تحتية", "شوارع", "جسور", "bridges", "drainage"],
        "landscape": ["لاند سكيب", "landscape", "حدائق", "تشجير", "زراعة", "ممشى", "garden", "park"],
        "automotive": ["سيارات", "automotive", "محطة وقود", "fuel station", "ورش", "workshop", "service center", "خدمة سيارات"],
        "industrial": ["مصنع", "factory", "industrial", "مستودع", "warehouse", "logistic", "صناعي"],
    }
    
    for category, kw_list in keywords.items():
        for kw in kw_list:
            if kw in t:
                scores[category] += 1
    
    # Return highest scoring (or 'general' if nothing matches)
    if max(scores.values()) == 0:
        return "general"
    return max(scores, key=scores.get)


def generate_realistic_projects(
    tender_text: str,
    company_name: str,
    num_projects: int = 5,
    seed: int = None
) -> dict:
    """
    يولّد مشاريع سابقة واقعية بناءً على نوع المناقصة.
    """
    # Set seed for consistent results per company
    if seed is None:
        seed = sum(ord(c) for c in company_name)
    random.seed(seed)
    
    # Detect type
    project_type = detect_project_type(tender_text)
    template = SECTOR_TEMPLATES.get(project_type, SECTOR_TEMPLATES["general"])
    
    # Generate projects
    current_year = datetime.now().year
    projects = []
    
    project_templates = template["projects"][:num_projects + 2]  # Slight variety
    random.shuffle(project_templates)
    
    for i, (title_tmpl, cost_tmpl, area_tmpl, year_tmpl) in enumerate(project_templates[:num_projects]):
        area = random.choice(ABU_DHABI_AREAS)
        cost = random.randint(*template["cost_range"])
        # Round cost to nearest 100k
        cost = round(cost / 100_000) * 100_000
        
        area_sqm = random.randint(*template["area_range"])
        # Round to nearest 50
        area_sqm = round(area_sqm / 50) * 50
        
        # Year: spread between 2020 and current year - 1
        year = current_year - 1 - i if i < 5 else current_year - 1 - random.randint(0, 5)
        if year < 2019:
            year = random.randint(2019, current_year - 1)
        
        title = title_tmpl.format(area=area)
        cost_str = cost_tmpl.format(cost=cost)
        area_str = area_tmpl.format(area_sqm=area_sqm)
        year_str = year_tmpl.format(year=year)
        
        projects.append({
            "id": i + 1,
            "title": title,
            "location": f"{area}، أبوظبي",
            "value_aed": cost,
            "value_text": cost_str,
            "area_text": area_str,
            "year": year,
            "year_text": year_str,
            "client": _random_client(project_type),
            "duration_months": random.choice([4, 6, 8, 10, 12, 14, 16, 18, 24]),
            "completion_status": "مكتمل ومسلّم",
            "description": _generate_description(title_tmpl, area),
        })
    
    # Sort by year descending (most recent first)
    projects.sort(key=lambda p: p["year"], reverse=True)
    
    return {
        "company_name": company_name,
        "project_type_detected": project_type,
        "project_type_ar": template["name_ar"],
        "total_projects": len(projects),
        "total_value_aed": sum(p["value_aed"] for p in projects),
        "projects": projects,
    }


def _random_client(project_type: str) -> str:
    """اختيار جهة عميل واقعية"""
    clients = {
        "contracting": [
            "شركة الدار العقارية", "شركة الإمارات للاستثمار", 
            "شركة عقار أبوظبي", "مستثمر خاص (سري)", "شركة الفنار للتطوير"
        ],
        "markets_retail": [
            "مجموعة الفطيم", "شركة لولو الدولية", "تجار محليون",
            "شركة المخازن المتحدة", "مستثمر خاص"
        ],
        "roads_infrastructure": [
            "بلدية مدينة أبوظبي", "هيئة الطرق والمواصلات",
            "دائرة البلديات والنقل DMT", "بلدية مدينة العين"
        ],
        "landscape": [
            "بلدية مدينة أبوظبي", "هيئة البيئة - أبوظبي",
            "مجموعة الإمارات للضيافة", "شركة عقارية خاصة"
        ],
        "automotive": [
            "شركة وكلاء سيارات", "مجموعة الحبتور للسيارات",
            "شركة الفطيم للسيارات", "مستثمر خاص"
        ],
        "industrial": [
            "ICAD - المدينة الصناعية", "موانئ أبوظبي ZonesCorp",
            "شركة مستثمرة خاصة", "مجموعة صناعية إماراتية"
        ],
        "general": [
            "شركة استثمارية إماراتية", "مستثمر خاص",
            "جهة حكومية", "شركة عقارية"
        ],
    }
    return random.choice(clients.get(project_type, clients["general"]))


def _generate_description(title_template: str, area: str) -> str:
    """وصف مختصر للمشروع"""
    descs = [
        "تنفيذ كامل المشروع من التصميم حتى التسليم النهائي حسب أعلى المعايير الإماراتية.",
        "إدارة مشروع متكاملة شملت التصميم، التراخيص، التنفيذ، والإشراف الفني.",
        "تنفيذ المشروع بنظام EPC مع تسليم مفتاح اليد للعميل في الموعد المتفق عليه.",
        "مشروع نموذجي تم تنفيذه بأعلى معايير الجودة والأمان وفقاً لاشتراطات الجهات الحكومية.",
        "تنفيذ المشروع شاملاً جميع الأعمال المدنية، الكهروميكانيكية، والتشطيبات النهائية.",
    ]
    return random.choice(descs)


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 smart_project_generator.py <tender_text_file> <company_name> <output.json>")
        sys.exit(1)
    
    tender_file = Path(sys.argv[1])
    company_name = sys.argv[2]
    output_file = Path(sys.argv[3])
    
    # Read tender text
    if tender_file.suffix == ".json":
        meta = json.loads(tender_file.read_text(encoding="utf-8"))
        tender_text = meta.get("raw_text", "") or json.dumps(meta, ensure_ascii=False)
    else:
        tender_text = tender_file.read_text(encoding="utf-8", errors="ignore")
    
    # Generate
    result = generate_realistic_projects(tender_text, company_name)
    
    # Save
    output_file.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    
    print(f"✅ Generated {result['total_projects']} projects")
    print(f"   Sector: {result['project_type_ar']} ({result['project_type_detected']})")
    print(f"   Total value: AED {result['total_value_aed']:,.0f}")
    for p in result['projects']:
        print(f"   • {p['title']} ({p['year']}) - {p['value_text']}")


if __name__ == "__main__":
    main()
