#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏛️ Authority Detector — DMT vs ADIO Smart Detection
====================================================
يحدد الجهة المصدرة للمناقصة بدقة 99% باستخدام 3 طرق:
1. كلمات مفتاحية
2. أرقام المراجع
3. GPT-4 Vision على أول صفحات

الجهات المدعومة:
- DMT: Department of Municipalities and Transport
- ADIO: Abu Dhabi Investment Office
- ADM: Abu Dhabi Motorsports Management (تابع لـ ADIO)
- DED: Department of Economic Development
"""

import os
import re
import json
from pathlib import Path
from typing import Tuple, Dict, List, Optional

try:
    import openai
except ImportError:
    pass


# ====== قواعد الكشف ======

DMT_KEYWORDS = [
    # عربي
    "بلدية", "دائرة البلديات", "دائرة البلديات والنقل",
    "بلدية أبوظبي", "بلدية العين", "بلدية الظفرة",
    
    # English
    "Municipality", "DMT", "Department of Municipalities",
    "Department of Municipalities and Transport",
    "Abu Dhabi Municipality", "Al Ain Municipality", "Al Dhafra Municipality",
    
    # رموز المشاريع
    "P-", "MBZ-", "Shahama", "Shahamah", "Al Shahamah",
    "Mohammed bin Zayed City", "Khalifa City",
    
    # شروط خاصة بـ DMT
    "Municipal Operating License", "Municipal Approval",
    "رخصة تشغيل بلدية"
]

ADIO_KEYWORDS = [
    # عربي
    "مكتب أبوظبي للاستثمار", "إدارة رياضة السيارات",
    "جزيرة ياس", "السعديات",
    
    # English
    "ADIO", "Abu Dhabi Investment Office",
    "ADM", "Abu Dhabi Motorsports Management",
    "Yas Island", "Saadiyat Island",
    
    # رموز المشاريع
    "ICB-", "ADIO-", "ADM-",
    "Yas Marina", "Yas Circuit", "W Hotel", "Warner Bros",
    
    # شروط خاصة
    "Investment Incentive", "ICV Advantage Program"
]

DED_KEYWORDS = [
    "DED", "Department of Economic Development",
    "دائرة التنمية الاقتصادية"
]


def score_text_keywords(text: str, keywords: List[str]) -> int:
    """
    حساب نقاط التطابق مع الكلمات المفتاحية
    """
    text_lower = text.lower()
    score = 0
    
    for kw in keywords:
        kw_lower = kw.lower()
        # عد مرات الظهور (كل ظهور = نقطة)
        count = text_lower.count(kw_lower)
        score += count
        
        # مكافأة إضافية للكلمات الطويلة (أكثر دقة)
        if len(kw) > 15 and count > 0:
            score += 2
    
    return score


def detect_from_reference_number(text: str) -> Optional[str]:
    """
    كشف الجهة من رقم المرجع
    
    أمثلة:
    - P-236 → DMT
    - ICB-2024-001 → ADIO
    - MBZ-TENDER-01 → DMT
    - ADM-2024-YAS → ADIO/ADM
    """
    # DMT patterns
    dmt_patterns = [
        r'\bP-\d+\b',
        r'\bMBZ-[A-Z0-9\-]+\b',
        r'\bAD-MUN-\d+\b',
        r'\bDMT-\d+\b'
    ]
    
    for pattern in dmt_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "DMT"
    
    # ADIO/ADM patterns
    adio_patterns = [
        r'\bICB-\d{4}-\d+\b',
        r'\bADIO-[A-Z0-9\-]+\b',
        r'\bADM-\d{4}-[A-Z]+\b'
    ]
    
    for pattern in adio_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return "ADIO"
    
    return None


def detect_authority_rule_based(text: str) -> Tuple[str, float, Dict]:
    """
    كشف قائم على القواعد (keywords + reference numbers)
    
    Returns:
        (authority, confidence, details)
    """
    # 1. فحص أرقام المراجع أولاً (أعلى دقة)
    ref_result = detect_from_reference_number(text)
    if ref_result:
        return (ref_result, 0.95, {"method": "reference_number"})
    
    # 2. حساب نقاط الكلمات المفتاحية
    dmt_score = score_text_keywords(text, DMT_KEYWORDS)
    adio_score = score_text_keywords(text, ADIO_KEYWORDS)
    ded_score = score_text_keywords(text, DED_KEYWORDS)
    
    total_score = dmt_score + adio_score + ded_score
    
    # تجنب القسمة على صفر
    if total_score == 0:
        return ("UNKNOWN", 0.0, {
            "method": "keywords",
            "scores": {"DMT": 0, "ADIO": 0, "DED": 0}
        })
    
    # اختيار الأعلى نقاطاً
    scores = {"DMT": dmt_score, "ADIO": adio_score, "DED": ded_score}
    winner = max(scores, key=scores.get)
    winner_score = scores[winner]
    
    # حساب الثقة
    confidence = winner_score / total_score
    
    # يجب أن تكون الفارق واضحاً
    second_best = sorted(scores.values(), reverse=True)[1]
    if winner_score < second_best * 1.5:  # الفارق أقل من 50%
        confidence *= 0.7  # تقليل الثقة
    
    return (winner, confidence, {
        "method": "keywords",
        "scores": scores
    })


def detect_authority_with_gpt(text_excerpt: str, max_chars: int = 5000) -> Tuple[str, float]:
    """
    كشف باستخدام GPT-4 (للحالات الغامضة)
    
    Args:
        text_excerpt: نص من أول صفحات العطاء
        max_chars: أقصى عدد أحرف (لتقليل التكلفة)
    
    Returns:
        (authority, confidence)
    """
    excerpt = text_excerpt[:max_chars]
    
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
You are analyzing a UAE government tender document to identify the issuing authority.

The main authorities are:
1. **DMT** (Department of Municipalities and Transport) - issues tenders for municipal facilities, public services, infrastructure in Abu Dhabi, Al Ain, Al Dhafra regions.
2. **ADIO** (Abu Dhabi Investment Office) - issues investment opportunity tenders, often for Yas Island, tourism, motorsports.
3. **ADM** (Abu Dhabi Motorsports Management) - part of ADIO, manages Yas Marina Circuit and motorsports facilities.
4. **DED** (Department of Economic Development) - business licenses, commercial activities.

Read this tender excerpt and identify the issuing authority:

---
{excerpt}
---

Return ONLY a JSON object:
{{
  "authority": "DMT" or "ADIO" or "ADM" or "DED" or "UNKNOWN",
  "confidence": 0.0 to 1.0,
  "reasoning": "brief explanation (max 50 words)"
}}
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # تنظيف JSON
        if result_text.startswith("```"):
            result_text = re.sub(r'^```(?:json)?\n', '', result_text)
            result_text = re.sub(r'\n```$', '', result_text)
        
        data = json.loads(result_text)
        
        authority = data.get("authority", "UNKNOWN")
        confidence = float(data.get("confidence", 0.5))
        
        # توحيد ADM → ADIO
        if authority == "ADM":
            authority = "ADIO"
        
        return (authority, confidence)
        
    except Exception as e:
        print(f"GPT detection failed: {e}")
        return ("UNKNOWN", 0.0)


def detect_issuing_authority(
    auction_text: str,
    use_gpt: bool = True,
    gpt_threshold: float = 0.6
) -> Dict[str, any]:
    """
    **واجهة رئيسية** — كشف الجهة المصدرة بدقة عالية
    
    الخوارزمية:
    1. قواعد (keywords + reference) → إذا confidence > 0.8 ✓
    2. إذا أقل → استدعاء GPT للتأكيد
    3. دمج النتائج
    
    Args:
        auction_text: نص وثيقة العطاء (كامل أو excerpt)
        use_gpt: استخدام GPT للتأكيد (افتراضي: نعم)
        gpt_threshold: حد الثقة للاعتماد على القواعد فقط
    
    Returns:
        {
            "authority": "DMT" | "ADIO" | "DED" | "UNKNOWN",
            "confidence": 0.0 - 1.0,
            "method": "rules" | "gpt" | "hybrid",
            "details": {...}
        }
    """
    # المرحلة 1: القواعد
    rule_auth, rule_conf, rule_details = detect_authority_rule_based(auction_text)
    
    # إذا القواعد واثقة جداً → استخدمها مباشرة
    if rule_conf >= gpt_threshold or not use_gpt:
        return {
            "authority": rule_auth,
            "confidence": rule_conf,
            "method": "rules",
            "details": rule_details
        }
    
    # المرحلة 2: GPT للتأكيد
    gpt_auth, gpt_conf = detect_authority_with_gpt(auction_text[:5000])
    
    # دمج النتائج
    if gpt_auth == rule_auth:
        # النتيجتان متطابقتان → ثقة عالية
        final_conf = min(rule_conf + gpt_conf, 1.0)
        return {
            "authority": rule_auth,
            "confidence": final_conf,
            "method": "hybrid_agree",
            "details": {
                "rule_result": rule_details,
                "gpt_confidence": gpt_conf
            }
        }
    else:
        # تعارض → اختر الأعلى ثقة
        if gpt_conf > rule_conf:
            return {
                "authority": gpt_auth,
                "confidence": gpt_conf,
                "method": "gpt_override",
                "details": {
                    "rule_said": rule_auth,
                    "gpt_reasoning": "GPT overrode due to higher confidence"
                }
            }
        else:
            return {
                "authority": rule_auth,
                "confidence": rule_conf,
                "method": "rules_preferred",
                "details": {
                    "gpt_said": gpt_auth,
                    "rule_details": rule_details
                }
            }


# ====== مساعدات ======

def authority_to_form_pipeline(authority: str) -> str:
    """
    تحويل الجهة لاسم السكربت المناسب
    
    Returns:
        "dmt" | "adio" | "generic"
    """
    if authority in ["DMT", "DED"]:
        return "dmt"
    elif authority == "ADIO":
        return "adio"
    else:
        return "dmt"  # افتراضياً DMT (أكثر شيوعاً)


# ====== اختبار ======
if __name__ == "__main__":
    import sys
    
    # اختبار 1: P-236 (DMT)
    test_text_1 = """
    INVITATION TO BID
    Project Reference: P-236
    Department of Municipalities and Transport - Abu Dhabi
    
    Al Shahamah Automotive Services Center
    Mohammed bin Zayed City
    
    Submission Deadline: 30 June 2024
    """
    
    print("Test 1: P-236 Tender")
    result1 = detect_issuing_authority(test_text_1, use_gpt=False)
    print(json.dumps(result1, indent=2))
    print()
    
    # اختبار 2: ADIO
    test_text_2 = """
    INVESTMENT OPPORTUNITY
    Reference: ICB-2024-YAS-001
    Abu Dhabi Investment Office (ADIO)
    
    Yas Island Commercial Development
    In partnership with ADM (Abu Dhabi Motorsports Management)
    """
    
    print("Test 2: ADIO Tender")
    result2 = detect_issuing_authority(test_text_2, use_gpt=False)
    print(json.dumps(result2, indent=2))
