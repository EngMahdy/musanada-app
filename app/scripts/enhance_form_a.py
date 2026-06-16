#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Form A Enhancer — يحسّن Form A بتصميم احترافي enterprise-grade

يستدعى بعد generate_adio_forms.py لتطبيق:
- Header/Footer احترافي
- Reference ID
- Page numbers
- تحسين كتلة التوقيع/الختم
"""

import sys
import json
from pathlib import Path
from datetime import datetime

try:
    from docx import Document
    from professional_formatter import (
        add_professional_header,
        add_professional_footer,
        generate_reference_id
    )
except ImportError as e:
    print(f"Error importing: {e}")
    sys.exit(1)


def enhance_form_a_document(docx_path: Path, company_data: dict, tender_no: str):
    """
    تحسين Form A الموجود بإضافة header/footer احترافي
    
    Args:
        docx_path: مسار ملف Form A
        company_data: بيانات الشركة
        tender_no: رقم المناقصة
    """
    print(f"📝 Enhancing Form A: {docx_path.name}")
    
    # فتح المستند
    doc = Document(str(docx_path))
    
    # 1. إضافة Header
    company_name_ar = company_data.get('legal_name', 'مساندة للاستشارات الهندسية ودراسات الجدوى')
    company_name_en = company_data.get('legal_name_en', 'MUSANADA Engineering Consultancy & Feasibility Studies')
    logo_path = company_data.get('_logo_path')
    
    ref_id = generate_reference_id(tender_no)
    
    add_professional_header(
        doc,
        logo_path=logo_path,
        company_name_ar=company_name_ar,
        company_name_en=company_name_en,
        ref_id=ref_id
    )
    
    # 2. إضافة Footer
    add_professional_footer(doc, company_data)
    
    # 3. حفظ النسخة المحسنة
    doc.save(str(docx_path))
    print(f"✅ Enhanced: {docx_path.name}")


def enhance_all_forms(output_dir: Path, company_data: dict, tender_no: str):
    """
    تحسين كل الفورمات في المجلد
    """
    form_files = list(output_dir.glob("Form_*.docx"))
    
    print(f"Found {len(form_files)} form files to enhance")
    
    for form_path in form_files:
        try:
            enhance_form_a_document(form_path, company_data, tender_no)
        except Exception as e:
            print(f"⚠️  Failed to enhance {form_path.name}: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhance Form A with professional formatting")
    parser.add_argument("output_dir", type=Path, help="Directory containing Form_*.docx files")
    parser.add_argument("--data", type=Path, help="Company data JSON file")
    parser.add_argument("--tender-no", type=str, default="P-XXX", help="Tender number")
    
    args = parser.parse_args()
    
    # قراءة بيانات الشركة
    if args.data and args.data.exists():
        with open(args.data, 'r', encoding='utf-8') as f:
            company_data = json.load(f)
    else:
        company_data = {}
    
    enhance_all_forms(args.output_dir, company_data, args.tender_no)
