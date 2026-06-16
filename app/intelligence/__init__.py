#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Intelligence Module — Entry point
"""

from .license_reader import extract_company_from_license, smart_fill_company_data
from .authority_detector import detect_issuing_authority, authority_to_form_pipeline
from .tender_parser import DeepTenderParser
from .orchestrator import run_full_intelligence

__all__ = [
    'extract_company_from_license',
    'smart_fill_company_data',
    'detect_issuing_authority',
    'authority_to_form_pipeline',
    'DeepTenderParser',
    'run_full_intelligence',
]
