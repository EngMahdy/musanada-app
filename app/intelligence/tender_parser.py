#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📖 Deep Tender Parser — فهم العطاء بالحرف
===========================================
يقرأ وثيقة العطاء صفحة بصفحة ويستخرج:

1. المتطلبات الفنية (Technical Requirements)
2. الشروط المالية (Financial Terms)
3. معايير التقييم (Evaluation Criteria)
4. الجداول الزمنية (Timeline)
5. الشروط الخاصة (Special Conditions)
6. ICV Requirements
7. Bonds & Guarantees
8. Penalties & Liquidated Damages

استراتيجية:
- تقسيم الوثيقة لأقسام (Volumes, Sections)
- استخراج جداول ومواصفات
- GPT-4 لفهم النصوص المعقدة
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

try:
    import openai
except ImportError:
    pass


# ====== استخراج الأقسام ======

def split_tender_into_sections(full_text: str, max_section_chars: int = 15000) -> Dict[str, str]:
    """
    تقسيم العطاء لأقسام منطقية
    
    الأقسام الشائعة:
    - Volume I: Instructions to Bidders
    - Volume II: Technical Specifications
    - Volume III: Feasibility Study (مطلوب من المتقدم)
    - Contract Conditions
    - Evaluation Criteria
    - Forms (A, B, D, E, G, H, ...)
    """
    sections = {}
    
    # Patterns للعناوين الرئيسية
    section_patterns = [
        (r'VOLUME\s+I\b', 'volume_1_instructions'),
        (r'VOLUME\s+II\b', 'volume_2_technical'),
        (r'VOLUME\s+III\b', 'volume_3_submission'),
        (r'(?:CONTRACT|AGREEMENT)\s+CONDITIONS', 'contract_conditions'),
        (r'TECHNICAL\s+SPECIFICATIONS?', 'technical_specs'),
        (r'EVALUATION\s+CRITERIA', 'evaluation'),
        (r'SCOPE\s+OF\s+WORK', 'scope_of_work'),
        (r'TERMS?\s+OF\s+REFERENCE', 'terms_of_reference'),
        (r'SPECIAL\s+CONDITIONS?', 'special_conditions'),
        (r'FINANCIAL\s+PROPOSAL', 'financial_proposal'),
    ]
    
    # محاولة تقسيم حسب العناوين
    last_pos = 0
    last_section = 'preamble'
    
    for i, (pattern, section_name) in enumerate(section_patterns):
        match = re.search(pattern, full_text, re.IGNORECASE)
        if match:
            # حفظ القسم السابق
            section_text = full_text[last_pos:match.start()]
            if section_text.strip():
                sections[last_section] = section_text[:max_section_chars]
            
            last_pos = match.start()
            last_section = section_name
    
    # حفظ القسم الأخير
    section_text = full_text[last_pos:]
    if section_text.strip():
        sections[last_section] = section_text[:max_section_chars]
    
    # إذا لم يتم تقسيم → استخدم النص كاملاً كـ "full_document"
    if len(sections) <= 1:
        sections['full_document'] = full_text[:max_section_chars * 3]
    
    return sections


# ====== استخراج المتطلبات الفنية ======

def extract_technical_requirements(text: str) -> Dict[str, Any]:
    """
    استخراج المواصفات الفنية من نص العطاء
    """
    tech = {}
    
    # المساحات
    area_patterns = [
        (r'(?:land|plot|site)\s+area[:\s]+(\d[\d,\.]+)\s*(?:square\s+meters?|sq\.?\s*m\.?|m2|sqm)', 'land_area_sqm'),
        (r'(?:building|construction)\s+area[:\s]+(\d[\d,\.]+)\s*(?:square\s+meters?|sq\.?\s*m\.?|m2|sqm)', 'building_area_sqm'),
        (r'(?:total|gross)\s+(?:built-up|floor)\s+area[:\s]+(\d[\d,\.]+)\s*(?:square\s+meters?|sq\.?\s*m\.?|m2|sqm)', 'gross_area_sqm'),
    ]
    
    for pattern, key in area_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '').replace('.', '')
            try:
                tech[key] = int(value_str)
            except:
                pass
    
    # مواقف السيارات
    parking_patterns = [
        r'(?:parking|car park)\s+(?:slots?|spaces?|bays?)[:\s]+(\d+)',
        r'(\d+)\s+(?:parking|car park)\s+(?:slots?|spaces?|bays?)',
    ]
    for pattern in parking_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                tech['parking_slots_required'] = int(match.group(1))
                break
            except:
                pass
    
    # ساعات التشغيل
    if re.search(r'24[/-]7|24\s*hours|round[- ]the[- ]clock', text, re.IGNORECASE):
        tech['operating_hours'] = '24/7'
    elif re.search(r'(\d{1,2})\s*(?:am|a\.m\.)\s*[-to]+\s*(\d{1,2})\s*(?:pm|p\.m\.)', text, re.IGNORECASE):
        match = re.search(r'(\d{1,2})\s*(?:am|a\.m\.)\s*[-to]+\s*(\d{1,2})\s*(?:pm|p\.m\.)', text, re.IGNORECASE)
        tech['operating_hours'] = f"{match.group(1)}:00 - {match.group(2)}:00"
    
    # Sustainability
    if re.search(r'ESTIDAMA|Pearl\s+\d|LEED|Green\s+Building', text, re.IGNORECASE):
        match = re.search(r'(?:ESTIDAMA\s+)?Pearl\s+(\d+)', text, re.IGNORECASE)
        if match:
            tech['sustainability_rating'] = f"ESTIDAMA Pearl {match.group(1)}"
        else:
            tech['sustainability_rating'] = 'Required'
    
    # ICV requirement
    if re.search(r'ICV|In[- ]Country\s+Value', text, re.IGNORECASE):
        tech['icv_required'] = True
        # محاولة استخراج النسبة
        match = re.search(r'(?:minimum|at least)\s+(\d+)%?\s+ICV', text, re.IGNORECASE)
        if match:
            tech['icv_minimum_percent'] = int(match.group(1))
    
    # Emirati staff requirement
    match = re.search(r'(?:minimum|at least)\s+(\d+)%?\s+(?:Emirati|UAE national)', text, re.IGNORECASE)
    if match:
        tech['emirati_staff_percent'] = int(match.group(1))
    
    return tech


def extract_technical_with_gpt(section_text: str) -> Dict[str, Any]:
    """
    استخراج دقيق باستخدام GPT-4 للمتطلبات الفنية
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are analyzing a UAE government tender's technical requirements section.

Extract the following information (use null if not found):

**Land & Buildings:**
- land_area_sqm: int (plot area in square meters)
- building_area_sqm: int (required building/construction area)
- parking_slots_required: int (minimum parking spaces)
- floors: int (number of floors/stories)

**Operations:**
- operating_hours: string (e.g., "24/7", "8:00-22:00", "As per Municipality regulations")
- operating_license_required: boolean
- facility_type: string (e.g., "Automotive Service Center", "Commercial Market", "Petrol Station")

**Facilities Required:** (list of strings)
- e.g., ["Vehicle inspection bays (8)", "Customer waiting lounge", "Prayer room", "Disabled access", "EV charging stations (4)"]

**Sustainability:**
- sustainability_rating: string (e.g., "ESTIDAMA Pearl 1", "LEED Silver")

**ICV & Localization:**
- icv_required: boolean
- icv_minimum_percent: int (minimum ICV score %)
- emirati_staff_percent: int (minimum % Emirati employees)

**Special Technical Conditions:** (list of strings)
- Any unique technical requirements mentioned

Return ONLY a valid JSON object with these keys.

---
TEXT:
{section_text[:8000]}
---
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1200,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # تنظيف JSON
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)
        
        data = json.loads(result_text)
        return data
        
    except Exception as e:
        print(f"GPT technical extraction failed: {e}")
        return {}


# ====== استخراج الشروط المالية ======

def extract_financial_terms(text: str) -> Dict[str, Any]:
    """
    استخراج الشروط المالية والتجارية
    """
    financial = {}
    
    # الإيجار السنوي الأدنى
    rent_patterns = [
        r'(?:minimum|min\.?)\s+(?:annual\s+)?rent[:\s]+(?:AED\s+)?(\d[\d,]+)',
        r'(?:annual\s+)?rent[:\s]+(?:AED\s+)?(\d[\d,]+)\s+(?:per\s+(?:annum|year))?',
    ]
    for pattern in rent_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                financial['min_annual_rent_aed'] = int(value_str)
                break
            except:
                pass
    
    # سعر المتر
    match = re.search(r'(\d+)\s*AED\s*(?:/|per)\s*(?:sq\.?\s*m|sqm|m2)', text, re.IGNORECASE)
    if match:
        try:
            financial['rent_per_sqm_aed'] = int(match.group(1))
        except:
            pass
    
    # نسبة الزيادة السنوية
    match = re.search(r'(?:escalation|increase)\s+(?:rate)?[:\s]+(\d+)%?', text, re.IGNORECASE)
    if match:
        try:
            financial['annual_escalation_percent'] = int(match.group(1))
        except:
            pass
    
    # فترة السماح
    grace_patterns = [
        r'grace\s+period[:\s]+(\d+)\s+(?:months?|years?)',
        r'(\d+)[-\s](?:month|year)\s+grace\s+period',
    ]
    for pattern in grace_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                financial['grace_period_months'] = int(match.group(1))
                break
            except:
                pass
    
    # مدة العقد
    contract_patterns = [
        r'contract\s+(?:period|duration|term)[:\s]+(\d+)\s+years?',
        r'(\d+)[-\s]year\s+contract',
    ]
    for pattern in contract_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                financial['contract_years'] = int(match.group(1))
                break
            except:
                pass
    
    # تأمينات
    match = re.search(r'(?:security|performance)\s+(?:deposit|bond)[:\s]+(\d+)%?', text, re.IGNORECASE)
    if match:
        try:
            financial['performance_bond_percent'] = int(match.group(1))
        except:
            pass
    
    return financial


# ====== استخراج معايير التقييم ======

def extract_evaluation_criteria(text: str) -> Dict[str, int]:
    """
    استخراج معايير التقييم ونسبها المئوية
    
    مثال:
    - Technical: 40%
    - Financial: 30%
    - Experience: 20%
    - ICV: 10%
    """
    criteria = {}
    
    # Patterns شائعة
    patterns = [
        (r'technical\s+(?:proposal|evaluation|score)[:\s]+(\d+)%?', 'technical_proposal'),
        (r'financial\s+(?:proposal|offer|evaluation)[:\s]+(\d+)%?', 'financial_offer'),
        (r'(?:company\s+)?experience[:\s]+(\d+)%?', 'company_experience'),
        (r'ICV\s+(?:score|certificate)?[:\s]+(\d+)%?', 'icv_score'),
        (r'(?:past\s+)?performance[:\s]+(\d+)%?', 'past_performance'),
    ]
    
    for pattern, key in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                criteria[key] = int(match.group(1))
            except:
                pass
    
    return criteria


# ====== استخراج الجداول الزمنية ======

def extract_timeline(text: str) -> Dict[str, str]:
    """
    استخراج التواريخ والجداول الزمنية المهمة
    """
    timeline = {}
    
    # تاريخ تقديم العروض
    submission_patterns = [
        r'submission\s+deadline[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
        r'(?:bids?|proposals?)\s+(?:must\s+be\s+)?submitted?\s+by[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    for pattern in submission_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            timeline['submission_deadline'] = match.group(1)
            break
    
    # فترة التشييد/التطوير
    construction_patterns = [
        r'construction\s+period[:\s]+(\d+)\s+(months?|days?)',
        r'development\s+period[:\s]+(\d+)\s+(months?|days?)',
    ]
    for pattern in construction_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            timeline['construction_period'] = f"{match.group(1)} {match.group(2)}"
            break
    
    # تاريخ بدء التشغيل
    commencement_patterns = [
        r'(?:commencement|operation\s+start)\s+date[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
    ]
    for pattern in commencement_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            timeline['operation_start_date'] = match.group(1)
            break
    
    return timeline


# ====== استخراج الشروط الخاصة ======

def extract_special_conditions_with_gpt(text: str) -> List[str]:
    """
    استخراج الشروط الخاصة والغريبة باستخدام GPT
    """
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
Read this tender document excerpt and extract ALL special conditions, unique requirements, mandatory obligations, and prohibitions.

Focus on:
- Prohibited activities (e.g., "No sale of alcohol", "No gambling")
- Mandatory licenses or certifications
- Revenue sharing requirements
- Reporting obligations
- Staffing requirements (Emiratization, minimum wages)
- Operating restrictions
- Compliance requirements
- Unique technical specifications

Return a JSON array of strings, each describing ONE special condition clearly and concisely (max 100 chars each).

Example output:
[
  "Operator must obtain Municipality Operating License within 30 days of contract signing",
  "Quarterly revenue reporting to DMT mandatory",
  "Minimum 30% Emirati staff required (ICV compliance)",
  "Prohibited: sale of alcohol, gambling services, tobacco products",
  "24/7 operation required, including public holidays",
  "Must include 4 EV charging stations (Tesla + CCS compatible)"
]

---
TEXT:
{text[:6000]}
---

Return ONLY the JSON array.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.2
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # تنظيف JSON
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)
        
        conditions = json.loads(result_text)
        
        if isinstance(conditions, list):
            return conditions
        else:
            return []
        
    except Exception as e:
        print(f"GPT special conditions extraction failed: {e}")
        return []


# ====== الواجهة الرئيسية ======

class DeepTenderParser:
    """
    محلل شامل لوثائق العطاءات
    """
    
    def __init__(self, use_gpt: bool = True):
        self.use_gpt = use_gpt
    
    def parse_full_tender(self, full_text: str) -> Dict[str, Any]:
        """
        تحليل كامل لوثيقة العطاء
        
        Returns:
            {
                "technical": {...},
                "financial": {...},
                "evaluation": {...},
                "timeline": {...},
                "special_conditions": [...]
            }
        """
        # تقسيم لأقسام
        sections = split_tender_into_sections(full_text)
        
        analysis = {}
        
        # 1. التقنية
        tech_section = sections.get('technical_specs') or sections.get('volume_2_technical') or sections.get('full_document', '')
        
        # استخراج قائم على القواعد
        tech_basic = extract_technical_requirements(tech_section)
        
        # تعزيز بـ GPT
        if self.use_gpt and tech_section:
            tech_gpt = extract_technical_with_gpt(tech_section)
            # دمج (GPT يأخذ الأولوية للحقول المعقدة)
            tech_basic.update(tech_gpt)
        
        analysis['technical'] = tech_basic
        
        # 2. المالية
        financial_section = sections.get('contract_conditions') or sections.get('financial_proposal') or sections.get('full_document', '')
        analysis['financial'] = extract_financial_terms(financial_section)
        
        # 3. التقييم
        eval_section = sections.get('evaluation') or sections.get('volume_1_instructions') or sections.get('full_document', '')
        analysis['evaluation'] = extract_evaluation_criteria(eval_section)
        
        # 4. الجدول الزمني
        analysis['timeline'] = extract_timeline(full_text)
        
        # 5. الشروط الخاصة
        special_section = sections.get('special_conditions') or sections.get('contract_conditions') or sections.get('full_document', '')
        if self.use_gpt and special_section:
            analysis['special_conditions'] = extract_special_conditions_with_gpt(special_section)
        else:
            analysis['special_conditions'] = []
        
        return analysis


# ====== اختبار ======
if __name__ == "__main__":
    import sys
    
    test_text = """
    TENDER DOCUMENT P-236
    
    Department of Municipalities and Transport - Abu Dhabi
    Al Shahamah Automotive Service Center
    
    TECHNICAL REQUIREMENTS:
    - Land Area: 6,503 square meters
    - Building Area: minimum 2,500 sqm
    - Parking: 120 slots required
    - Operating Hours: 24/7 including public holidays
    - Facilities Required:
      * Vehicle inspection bays (minimum 8)
      * Customer waiting lounge
      * Prayer room
      * Disabled access ramps
      * EV charging stations (minimum 4, Tesla + CCS compatible)
    - Sustainability: ESTIDAMA Pearl 1 Rating minimum
    
    FINANCIAL TERMS:
    - Minimum Annual Rent: AED 552,755
    - Rent Calculation: 6,503 sqm × 85 AED/sqm/year
    - Contract Period: 25 years
    - Grace Period: 12 months (first year rent-free)
    - Annual Escalation: 2% per year
    - Performance Bond: 10% of annual rent
    
    EVALUATION CRITERIA:
    - Technical Proposal: 40%
    - Financial Offer: 30%
    - Company Experience: 20%
    - ICV Certificate: 10%
    
    TIMELINE:
    - Submission Deadline: 30/06/2024 14:00 GST
    - Construction Period: 6 months
    - Operation Start: 01/01/2025
    
    SPECIAL CONDITIONS:
    - Operator must obtain Municipality Operating License within 30 days
    - Minimum 30% Emirati staff (ICV compliance)
    - Quarterly revenue reporting to DMT mandatory
    - Prohibited: sale of alcohol, gambling services
    """
    
    parser = DeepTenderParser(use_gpt=False)
    result = parser.parse_full_tender(test_text)
    
    print(json.dumps(result, indent=2, ensure_ascii=False))
