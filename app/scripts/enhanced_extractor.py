#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Tender Extractor — يدمج:
1. License OCR (قراءة الرخصة تلقائياً)
2. Authority Detection (DMT vs ADIO ذكي)
3. Deep Parsing (استخراج تفاصيل العطاء بالحرف)

يُستدعى من main.py قبل extract_tender.py الأصلي
"""

import sys
import json
from pathlib import Path

# إضافة app/ للـpath
APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR.parent))

from app.intelligence import (
    extract_company_from_license,
    smart_fill_company_data,
    detect_issuing_authority,
    DeepTenderParser,
)


def enhance_extraction(
    job_dir: Path,
    company_data: dict,
    tender_files: list
) -> dict:
    """
    تحسين الاستخراج باستخدام Intelligence Modules
    
    Args:
        job_dir: مجلد العملية
        company_data: بيانات الشركة المدخلة (قد تكون فارغة)
        tender_files: قائمة ملفات العطاء
    
    Returns:
        {
            "company_data": {...},  # محسّنة من الرخصة
            "authority": "DMT"|"ADIO",
            "tender_analysis": {...}  # deep parsing
        }
    """
    result = {
        "company_data": company_data.copy(),
        "authority": "UNKNOWN",
        "tender_analysis": {}
    }
    
    # ===== 1. OCR للرخصة =====
    license_dir = job_dir / "attachments" / "license"
    if license_dir.exists():
        license_files = list(license_dir.glob("*"))
        if license_files:
            print(f"🔍 Found {len(license_files)} license file(s), extracting...")
            license_file = license_files[0]
            
            try:
                license_data = extract_company_from_license(license_file, use_vision=True)
                print(f"✅ Extracted from license: {list(license_data.keys())}")
                
                # دمج ذكي مع بيانات المستخدم
                result["company_data"] = smart_fill_company_data(company_data, license_data)
                
            except Exception as e:
                print(f"⚠️  License extraction failed: {e}")
    
    # ===== 2. Authority Detection =====
    # قراءة أول ملف عطاء
    auction_text = ""
    for tf in tender_files:
        if tf.exists() and tf.suffix.lower() in ['.pdf', '.txt', '.docx']:
            try:
                # استخراج نص بسيط
                if tf.suffix.lower() == '.pdf':
                    import subprocess
                    proc = subprocess.run(
                        ['pdftotext', str(tf), '-'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if proc.returncode == 0:
                        auction_text = proc.stdout
                        break
            except:
                pass
    
    if auction_text:
        try:
            auth_result = detect_issuing_authority(auction_text, use_gpt=True)
            result["authority"] = auth_result["authority"]
            result["authority_confidence"] = auth_result["confidence"]
            result["authority_method"] = auth_result["method"]
            
            print(f"✅ Authority detected: {auth_result['authority']} "
                  f"(confidence: {auth_result['confidence']:.0%}, "
                  f"method: {auth_result['method']})")
            
        except Exception as e:
            print(f"⚠️  Authority detection failed: {e}")
    
    # ===== 3. Deep Parsing =====
    if auction_text:
        try:
            parser = DeepTenderParser(use_gpt=True)
            tender_analysis = parser.parse_full_tender(auction_text)
            result["tender_analysis"] = tender_analysis
            
            print(f"✅ Tender parsed:")
            print(f"  - Technical: {len(tender_analysis.get('technical', {}))} fields")
            print(f"  - Financial: {len(tender_analysis.get('financial', {}))} fields")
            print(f"  - Evaluation: {len(tender_analysis.get('evaluation', {}))} criteria")
            print(f"  - Special Conditions: {len(tender_analysis.get('special_conditions', []))} items")
            
        except Exception as e:
            print(f"⚠️  Tender parsing failed: {e}")
    
    return result


# ====== واجهة CLI ======
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Tender Extraction")
    parser.add_argument("job_dir", type=Path, help="Job directory")
    parser.add_argument("--output", type=Path, help="Output JSON file", default=None)
    
    args = parser.parse_args()
    
    # قراءة company data من form_snapshot.json
    snapshot_file = args.job_dir / "form_snapshot.json"
    if snapshot_file.exists():
        with open(snapshot_file, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)
            company_data = {
                k: v for k, v in snapshot.items()
                if k.startswith('company_') or k in ['legal_name', 'license_number', 'establishment_date']
            }
    else:
        company_data = {}
    
    # قراءة tender files
    tender_input_dir = args.job_dir / "tender_input"
    tender_files = list(tender_input_dir.glob("*")) if tender_input_dir.exists() else []
    
    # تشغيل Enhancement
    result = enhance_extraction(args.job_dir, company_data, tender_files)
    
    # حفظ النتيجة
    output_file = args.output or (args.job_dir / "enhanced_meta.json")
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Enhanced metadata saved to: {output_file}")
