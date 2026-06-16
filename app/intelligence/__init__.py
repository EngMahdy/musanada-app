"""
Musanada Tender Intelligence Module
====================================
وحدة دراسة المناقصات الذكية: 5 محللات تعمل بالتوازي.

Modules:
- technical   : تحليل المتطلبات الفنية من Auction Document
- financial   : تحليل مالي CAPEX/OPEX/IRR/NPV/Payback
- market      : بحث ويب حي - أسعار إيجارات + منافسين
- strategic   : SWOT + مخاطر + توصية مبدئية
- summary     : ملخص تنفيذي Go/No-Go بصفحتين

Entry point: run_full_intelligence(tender_data, company_data, user_inputs)
"""

from .orchestrator import run_full_intelligence  # noqa: F401
