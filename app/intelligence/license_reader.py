#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📄 License Reader — OCR + GPT Vision
====================================
يستخرج بيانات الشركة تلقائياً من صورة الرخصة التجارية (PDF/JPG/PNG)

المخرجات:
- Legal Name (الاسم القانوني)
- License Number (رقم الرخصة)
- Establishment Date (تاريخ التأسيس)
- Activities (النشاط)
- Owner/Partners (المالك/الشركاء)
- Expiry Date (تاريخ الانتهاء)
- Issuing Authority (الجهة المصدرة)
- Address (العنوان)
"""

import base64
import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, List

try:
    import openai
    from PIL import Image
    import pdf2image
except ImportError:
    pass


def extract_license_data_vision(file_path: Path) -> Dict[str, str]:
    """
    استخراج بيانات الرخصة باستخدام GPT-4 Vision
    
    Args:
        file_path: مسار ملف الرخصة (PDF/JPG/PNG)
    
    Returns:
        dict: بيانات الشركة المستخرجة
    """
    # تحويل PDF لصورة إذا لزم الأمر
    if file_path.suffix.lower() == '.pdf':
        images = pdf2image.convert_from_path(str(file_path), first_page=1, last_page=1, dpi=300)
        img = images[0]
        # حفظ مؤقت
        temp_img = file_path.parent / f"{file_path.stem}_page1.jpg"
        img.save(temp_img, 'JPEG', quality=95)
        image_path = temp_img
    else:
        image_path = file_path
    
    # تحويل لـ base64
    with open(image_path, 'rb') as f:
        img_data = base64.b64encode(f.read()).decode('utf-8')
    
    # استدعاء GPT-4 Vision
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = """
You are an expert in reading UAE Commercial License documents (Arabic/English).

Extract the following information from this license image:

1. **Legal Name** (الاسم القانوني) - full legal company name in Arabic
2. **Legal Name (English)** - company name in English (if available)
3. **License Number** (رقم الرخصة) - the license/registration number
4. **Establishment Date** (تاريخ التأسيس) - date of establishment (format: YYYY-MM-DD)
5. **Expiry Date** (تاريخ الانتهاء) - license expiry date (format: YYYY-MM-DD)
6. **Activities** (النشاط) - main business activities (Arabic + English)
7. **Owner/Partners** (المالك/الشركاء) - owner or partner names
8. **Issuing Authority** (الجهة المصدرة) - issuing authority (e.g., DED, ADM, ADDED)
9. **Address** (العنوان) - registered address
10. **Legal Form** (الشكل القانوني) - e.g., LLC, Sole Proprietorship, etc.

Return ONLY a valid JSON object with these keys (use null if not found):
{
  "legal_name_ar": "...",
  "legal_name_en": "...",
  "license_number": "...",
  "establishment_date": "YYYY-MM-DD",
  "expiry_date": "YYYY-MM-DD",
  "activities_ar": "...",
  "activities_en": "...",
  "owner": "...",
  "issuing_authority": "...",
  "address": "...",
  "legal_form": "..."
}

IMPORTANT:
- For dates, use ISO format (YYYY-MM-DD)
- If you see Hijri dates, convert to Gregorian
- Extract ALL activities listed
- Be precise with license numbers (include hyphens/spaces as shown)
"""
    
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1500,
        temperature=0.1
    )
    
    # استخراج JSON من الإجابة
    result_text = response.choices[0].message.content.strip()
    
    # إزالة markdown code blocks إذا وجدت
    if result_text.startswith("```"):
        result_text = re.sub(r'^```(?:json)?\n', '', result_text)
        result_text = re.sub(r'\n```$', '', result_text)
    
    try:
        data = json.loads(result_text)
    except json.JSONDecodeError:
        # محاولة استخراج JSON من النص
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            raise ValueError(f"Failed to parse Vision API response: {result_text}")
    
    # تنظيف البيانات
    cleaned = {}
    
    # الاسم القانوني
    if data.get('legal_name_ar'):
        cleaned['legal_name'] = data['legal_name_ar']
    elif data.get('legal_name_en'):
        cleaned['legal_name'] = data['legal_name_en']
    else:
        cleaned['legal_name'] = None
    
    cleaned['legal_name_en'] = data.get('legal_name_en')
    
    # رقم الرخصة
    cleaned['license_number'] = data.get('license_number')
    
    # تاريخ التأسيس
    est_date = data.get('establishment_date')
    if est_date and est_date != 'null':
        cleaned['establishment_date'] = est_date
    else:
        cleaned['establishment_date'] = None
    
    # تاريخ الانتهاء
    exp_date = data.get('expiry_date')
    if exp_date and exp_date != 'null':
        cleaned['expiry_date'] = exp_date
    else:
        cleaned['expiry_date'] = None
    
    # النشاط
    activities = []
    if data.get('activities_ar'):
        activities.append(data['activities_ar'])
    if data.get('activities_en') and data.get('activities_en') != data.get('activities_ar'):
        activities.append(data['activities_en'])
    
    cleaned['activity'] = ' | '.join(activities) if activities else None
    
    # المالك
    cleaned['owner'] = data.get('owner')
    
    # الجهة المصدرة
    cleaned['issuing_authority'] = data.get('issuing_authority')
    
    # العنوان
    cleaned['address'] = data.get('address')
    
    # الشكل القانوني
    cleaned['legal_form'] = data.get('legal_form')
    
    # حذف الصورة المؤقتة
    if file_path.suffix.lower() == '.pdf':
        temp_img.unlink(missing_ok=True)
    
    return cleaned


def smart_fill_company_data(
    existing_data: Dict[str, str],
    license_data: Dict[str, str]
) -> Dict[str, str]:
    """
    دمج ذكي بين بيانات المستخدم وبيانات الرخصة
    
    القاعدة:
    - إذا المستخدم كتب حاجة → استخدمها
    - إذا الخانة فاضية → املاها من الرخصة
    - إذا الرخصة فيها معلومات إضافية → أضفها
    """
    result = existing_data.copy()
    
    # الاسم القانوني
    if not result.get('legal_name') or result.get('legal_name') == '':
        result['legal_name'] = license_data.get('legal_name')
    
    # الاسم المختصر (إذا فاضي → استخدم الاسم الإنجليزي)
    if not result.get('short_name') or result.get('short_name') == '':
        if license_data.get('legal_name_en'):
            # أخذ أول 3 كلمات
            words = license_data['legal_name_en'].split()[:3]
            result['short_name'] = ' '.join(words)
    
    # رقم الرخصة
    if not result.get('license_number') or result.get('license_number') == '':
        result['license_number'] = license_data.get('license_number')
    
    # تاريخ التأسيس
    if not result.get('establishment_date') or result.get('establishment_date') == '':
        result['establishment_date'] = license_data.get('establishment_date')
    
    # النشاط
    if not result.get('activity') or result.get('activity') == '':
        result['activity'] = license_data.get('activity')
    
    # العنوان
    if not result.get('address') or result.get('address') == '':
        result['address'] = license_data.get('address')
    
    # الشكل القانوني
    if not result.get('legal_form') or result.get('legal_form') == '':
        result['legal_form'] = license_data.get('legal_form')
    
    # المالك (للرجوع إليه)
    if license_data.get('owner'):
        result['_license_owner'] = license_data['owner']
    
    # الجهة المصدرة
    if license_data.get('issuing_authority'):
        result['_license_issuer'] = license_data['issuing_authority']
    
    return result


def extract_license_quick_fallback(file_path: Path) -> Dict[str, str]:
    """
    استخراج سريع بـ OCR فقط (fallback إذا Vision API فشل)
    """
    try:
        import pytesseract
        from PIL import Image
        
        if file_path.suffix.lower() == '.pdf':
            images = pdf2image.convert_from_path(str(file_path), first_page=1, last_page=1)
            img = images[0]
        else:
            img = Image.open(file_path)
        
        # OCR بالعربي + الإنجليزي
        text = pytesseract.image_to_string(img, lang='ara+eng')
        
        # استخراج patterns بسيطة
        data = {}
        
        # رقم الرخصة
        license_patterns = [
            r'(?:رقم الرخصة|License No\.?|Registration No\.?)[:\s]*([A-Z0-9\-]+)',
            r'CN[- ]?\d+',
            r'COM[- ]?\d+',
        ]
        for pattern in license_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                data['license_number'] = match.group(1) if match.lastindex else match.group()
                break
        
        return data
        
    except Exception as e:
        print(f"OCR fallback failed: {e}")
        return {}


# ====== واجهة عامة ======

def extract_company_from_license(
    file_path: Path,
    use_vision: bool = True
) -> Dict[str, str]:
    """
    واجهة رئيسية لاستخراج بيانات الشركة من الرخصة
    
    Args:
        file_path: مسار ملف الرخصة
        use_vision: استخدام GPT Vision (افتراضي: نعم)
    
    Returns:
        dict: بيانات الشركة
    """
    if use_vision:
        try:
            return extract_license_data_vision(file_path)
        except Exception as e:
            print(f"Vision API failed, trying OCR fallback: {e}")
            return extract_license_quick_fallback(file_path)
    else:
        return extract_license_quick_fallback(file_path)


# ====== اختبار ======
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python license_reader.py <license_file.pdf>")
        sys.exit(1)
    
    file_path = Path(sys.argv[1])
    
    print("🔍 Extracting license data...")
    data = extract_company_from_license(file_path)
    
    print("\n📋 Extracted Data:")
    print(json.dumps(data, indent=2, ensure_ascii=False))
