"""
Musanada Engineering Consultancy — Tender Package Generator
Production-ready FastAPI app for deployment on Render/Railway.
"""

import os
import sys
import json
import shutil
import zipfile
import subprocess
import uuid
import re
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ============ CONFIG ============
APP_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = APP_DIR / "templates"
BRAND_DIR = APP_DIR / "brand"
SCRIPTS_DIR = APP_DIR / "scripts"
DATA_DIR = APP_DIR / "data"

# On Render, use /tmp for outputs (ephemeral but writable)
OUTPUTS_DIR = Path(os.environ.get("OUTPUTS_DIR", "/tmp/musanada_outputs"))
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Apt-installed binaries
PDFTOTEXT = "pdftotext"
SEVENZ = "7z"

# ============ APP ============
app = FastAPI(title="Musanada Engineering Consultancy")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Static files
app.mount("/static", StaticFiles(directory=str(BRAND_DIR)), name="static")
app.mount("/outputs", StaticFiles(directory=str(OUTPUTS_DIR)), name="outputs")


# ============ ROUTES ============
@app.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text(encoding="utf-8")
    return html


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "musanada-app",
        "version": "1.0.0",
        "ts": datetime.now().isoformat()
    }


@app.post("/api/process")
async def process_tender(
    tender_file: UploadFile = File(...),
    company_legal_name: str = Form(...),
    company_short_name: str = Form(""),
    legal_form: str = Form(...),
    establishment_date: str = Form(...),
    nature_of_business: str = Form(...),
    hq_address: str = Form(...),
    company_phone: str = Form(""),
    company_fax: str = Form(""),
    company_email: str = Form(...),
    company_website: str = Form(""),
    trade_license_no: str = Form(...),
    authorized_signatory_name: str = Form(...),
    authorized_signatory_title: str = Form(...),
    contact_person_name: str = Form(""),
    contact_person_phone: str = Form(""),
    contact_person_email: str = Form(""),
    years_experience: str = Form(""),
    experience_domain: str = Form(""),
    logo: UploadFile = File(None),
    signature: UploadFile = File(None),
    stamp: UploadFile = File(None),
    proj_name: list = Form([]),
    proj_location: list = Form([]),
    proj_scope: list = Form([]),
    proj_amount: list = Form([]),
    proj_start: list = Form([]),
    proj_end: list = Form([]),
    proj_gfa: list = Form([]),
):
    """Main processing endpoint."""
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUTS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # ===== STEP 1: Save tender file =====
        tender_path = job_dir / "input_tender.zip"
        with open(tender_path, "wb") as f:
            shutil.copyfileobj(tender_file.file, f)
        
        # ===== STEP 2: Save images =====
        images_dir = job_dir / "images"
        images_dir.mkdir(exist_ok=True)
        logo_path = None
        sig_path = None
        stamp_path = None
        
        if logo and logo.filename:
            logo_path = images_dir / f"logo{Path(logo.filename).suffix}"
            with open(logo_path, "wb") as f:
                shutil.copyfileobj(logo.file, f)
        
        if signature and signature.filename:
            sig_path = images_dir / f"signature{Path(signature.filename).suffix}"
            with open(sig_path, "wb") as f:
                shutil.copyfileobj(signature.file, f)
        
        if stamp and stamp.filename:
            stamp_path = images_dir / f"stamp{Path(stamp.filename).suffix}"
            with open(stamp_path, "wb") as f:
                shutil.copyfileobj(stamp.file, f)
        
        # ===== STEP 3: Build bidder_data.json =====
        projects = []
        for i in range(len(proj_name)):
            name = proj_name[i] if i < len(proj_name) else ""
            if not name.strip():
                continue
            projects.append({
                "name": name,
                "location": proj_location[i] if i < len(proj_location) else "",
                "scope": proj_scope[i] if i < len(proj_scope) else "",
                "amount": int(proj_amount[i]) if i < len(proj_amount) and proj_amount[i] else 0,
                "start": proj_start[i] if i < len(proj_start) else "",
                "end": proj_end[i] if i < len(proj_end) else "",
                "gfa": int(proj_gfa[i]) if i < len(proj_gfa) and proj_gfa[i] else 0,
                "gla": int(int(proj_gfa[i]) * 0.92) if i < len(proj_gfa) and proj_gfa[i] else 0,
                "status": "Built 100%",
                "dev_role": "YES", "leasing_role": "YES", "mgmt_role": "YES",
                "floor_eff": "92%", "occ_2022": "85%", "occ_2023": "90%",
            })
        
        bidder_data = {
            "company_legal_name": company_legal_name,
            "company_short_name": company_short_name,
            "legal_form": legal_form,
            "establishment_date": establishment_date,
            "nature_of_business": nature_of_business,
            "hq_address": hq_address,
            "bidder_address": hq_address,
            "partners_nationality": "UAE",
            "company_phone": company_phone,
            "company_fax": company_fax,
            "company_email": company_email,
            "company_website": company_website,
            "trade_license_no": trade_license_no,
            "authorized_signatory_name": authorized_signatory_name,
            "authorized_signatory_title": authorized_signatory_title,
            "contact_person_name": contact_person_name or authorized_signatory_name,
            "contact_person_phone": contact_person_phone or company_phone,
            "contact_person_email": contact_person_email or company_email,
            "min_exp_years": 2,
            "experience_domain": experience_domain or "building and operating similar facilities",
            "years_experience": years_experience,
            "submission_date": datetime.now().strftime("%d-%m-%Y"),
            "projects_completed": projects,
            "projects_current": [],
            "architect": {"firm_name": "Selected Architectural Firm", "specialty": "Commercial Architecture"},
            "architect_projects": [],
            "logo_path": str(logo_path) if logo_path else None,
            "signature_image_path": str(sig_path) if sig_path else None,
            "stamp_image_path": str(stamp_path) if stamp_path else None,
        }
        
        bidder_data_path = job_dir / "bidder_data.json"
        bidder_data_path.write_text(json.dumps(bidder_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # ===== STEP 4: Extract tender =====
        extracted_dir = job_dir / "extracted_tender"
        extracted_dir.mkdir(exist_ok=True)
        try:
            with zipfile.ZipFile(tender_path, 'r') as z:
                z.extractall(extracted_dir)
        except zipfile.BadZipFile:
            # Maybe a PDF
            shutil.copy2(tender_path, extracted_dir / "tender.pdf")
        
        # ===== STEP 5: Run extract_tender.py =====
        workspace_dir = job_dir / "workspace"
        workspace_dir.mkdir(exist_ok=True)
        
        if any(p.is_dir() for p in extracted_dir.iterdir()):
            input_dir = extracted_dir
        else:
            single = extracted_dir / "Tender"
            single.mkdir(exist_ok=True)
            for f in extracted_dir.iterdir():
                if f.is_file():
                    shutil.move(str(f), str(single / f.name))
            input_dir = extracted_dir
        
        run_cmd(["python3", str(SCRIPTS_DIR / "extract_tender.py"), str(input_dir), str(workspace_dir)])
        
        # ===== STEP 6: Build analysis =====
        run_cmd(["python3", str(SCRIPTS_DIR / "build_analysis.py"), str(workspace_dir)])
        
        # Find tender dirs
        tender_dirs = [d for d in workspace_dir.iterdir() 
                       if d.is_dir() and (d / "tender_meta.json").exists()]
        if not tender_dirs:
            raise HTTPException(500, "Could not extract tender data from the file")
        
        # ===== STEP 7+: Process each tender =====
        all_outputs = []
        
        for tender_dir in tender_dirs:
            meta = json.loads((tender_dir / "tender_meta.json").read_text(encoding="utf-8"))
            tender_name = meta.get("auction_title", tender_dir.name)
            safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in tender_name)[:60].strip()
            
            forms_data = dict(bidder_data)
            forms_data["tender_no"] = meta.get("auction_title", "")[:30]
            forms_data["tender_name"] = tender_name
            
            forms_dir = job_dir / "results" / safe_name / "01_Forms"
            forms_dir.mkdir(parents=True, exist_ok=True)
            
            forms_data_path = job_dir / f"forms_data_{safe_name}.json"
            forms_data_path.write_text(json.dumps(forms_data, ensure_ascii=False, indent=2), encoding="utf-8")
            
            run_cmd(["python3", str(SCRIPTS_DIR / "generate_adio_forms.py"), 
                     str(forms_data_path), str(forms_dir)])
            
            # Financial Model
            financial_dir = job_dir / "results" / safe_name / "02_Financial_Model"
            financial_dir.mkdir(parents=True, exist_ok=True)
            
            meta["tender_name"] = tender_name
            meta["issuing_authority"] = "DMT" if "DMT" in tender_name or "Auction Document" in tender_name else "ADIO"
            meta["land_area_sqm"] = float(str(meta.get("land_area_sqm", "5000")).replace(",", "") or "5000")
            meta["min_rent_per_sqm"] = float(str(meta.get("min_rent_per_sqm", "100")).replace(",", "") or "100")
            meta["contract_years"] = int(meta.get("contract_years", 25))
            meta["grace_period_years"] = int(meta.get("grace_period_years", 1))
            meta["annual_escalation_govt"] = 0.02
            (tender_dir / "tender_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
            
            financial_excel = financial_dir / f"Financial_Model_{safe_name}.xlsx"
            run_cmd(["python3", str(SCRIPTS_DIR / "financial_model.py"),
                     str(tender_dir / "tender_meta.json"), str(financial_excel)])
            
            # Architectural renders (skip if no AI key)
            plans_dir = job_dir / "results" / safe_name / "03_Architectural"
            plans_dir.mkdir(parents=True, exist_ok=True)
            try:
                generate_architectural(meta, plans_dir, safe_name)
            except Exception as e:
                print(f"Architectural generation skipped: {e}")
                # Create placeholders instead
                create_placeholder_images(plans_dir, meta)
            
            # Copy analysis
            analysis_dest = job_dir / "results" / safe_name / "04_Analysis"
            analysis_dest.mkdir(parents=True, exist_ok=True)
            
            analysis_src = tender_dir / "analysis_AR.md"
            if analysis_src.exists():
                shutil.copy2(analysis_src, analysis_dest / "Analysis_AR.md")
            shutil.copy2(forms_data_path, analysis_dest / "bidder_data.json")
            
            # README
            readme_path = job_dir / "results" / safe_name / "00_README.md"
            readme_path.write_text(build_tender_readme(meta, bidder_data), encoding="utf-8")
            
            all_outputs.append(safe_name)
        
        # Final ZIP
        final_zip = OUTPUTS_DIR / f"Musanada_Package_{job_id}.zip"
        with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED) as zf:
            results_root = job_dir / "results"
            for fp in results_root.rglob("*"):
                if fp.is_file():
                    zf.write(fp, fp.relative_to(results_root))
        
        # Build response
        files = [{
            "name": f"Musanada_Package_{job_id}.zip",
            "url": f"/outputs/Musanada_Package_{job_id}.zip",
            "description": f"الحزمة الكاملة ({len(all_outputs)} مناقصة)"
        }]
        
        for tender_name in all_outputs[:1]:
            results_dir = job_dir / "results" / tender_name
            for fp in (results_dir).rglob("*"):
                if fp.is_file() and fp.suffix.lower() in [".docx", ".xlsx", ".pdf", ".png", ".md"]:
                    rel = fp.relative_to(results_dir)
                    files.append({
                        "name": fp.name,
                        "url": f"/outputs/{job_id}/results/{tender_name}/{rel}",
                        "description": describe_file(fp.name)
                    })
        
        return JSONResponse({
            "status": "ok",
            "job_id": job_id,
            "tenders_processed": len(all_outputs),
            "files": files
        })
    
    except subprocess.CalledProcessError as e:
        return JSONResponse({
            "status": "error",
            "message": f"خطأ في تشغيل سكريبت: {Path(e.cmd[1]).name if len(e.cmd) > 1 else e.cmd[0]}",
            "details": (e.stderr or "")[:500],
        }, status_code=500)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()[:1000]
        }, status_code=500)


# ============ HELPERS ============
def run_cmd(cmd, cwd=None):
    print(f">>> Running: {Path(cmd[1]).name if len(cmd)>1 else ' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"STDERR: {result.stderr[:500]}")
        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
    return result


def describe_file(filename):
    lower = filename.lower()
    if "form_a" in lower: return "خطاب الغلاف"
    if "form_d" in lower: return "بيانات المزايد"
    if "form_e" in lower: return "الإعلان المحلف"
    if "form_g" in lower: return "خبرة المشاريع التفصيلية"
    if "form_h" in lower: return "خبرة المعماري"
    if "folder1" in lower: return "قائمة تدقيق - المتطلبات المسبقة"
    if "folder2" in lower: return "قائمة تدقيق - العرض الفني"
    if "folder3" in lower: return "قائمة تدقيق - العرض المالي"
    if "financial_model" in lower or ".xlsx" in lower: return "النموذج المالي"
    if "site_plan" in lower: return "المخطط الموقعي"
    if "perspective" in lower: return "منظور 3D"
    if "facade" in lower: return "الواجهة المعمارية"
    if "interior" in lower: return "المنظور الداخلي"
    if "analysis" in lower: return "التحليل العربي"
    if "readme" in lower: return "دليل الحزمة"
    return ""


def build_tender_readme(meta, bidder):
    return f"""# {meta.get('auction_title', 'Tender Package')}

> **حزمة تجهيز المناقصة الكاملة**  
> تم إعدادها بواسطة: مساندة للاستشارات الهندسية  
> التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}

---

## 🏢 الشركة المتقدمة
- **الاسم:** {bidder.get('company_legal_name', '-')}
- **الترخيص:** {bidder.get('trade_license_no', '-')}
- **الممثل المفوض:** {bidder.get('authorized_signatory_name', '-')} ({bidder.get('authorized_signatory_title', '-')})

## 📋 المناقصة
- **الجهة:** {meta.get('issuing_authority', '-')}
- **الموقع:** {meta.get('location', '-')}
- **المساحة:** {meta.get('land_area_sqm', '-')} م²
- **الحد الأدنى للإيجار:** AED {meta.get('min_rent_per_sqm', '-')}/م²
- **بدل المناقصة (+20%):** AED {float(meta.get('min_rent_per_sqm', 100)) * 1.2:.2f}/م²
- **آخر موعد:** {meta.get('closing_date', '-')}

## 📁 محتويات المجلد

| # | المجلد | الوصف |
|---|--------|------|
| 01 | `01_Forms/` | 8 نماذج جاهزة للتوقيع |
| 02 | `02_Financial_Model/` | نموذج Excel مالي بـ 10 شيتات |
| 03 | `03_Architectural/` | المخطط الموقعي + المنظور 3D |
| 04 | `04_Analysis/` | التحليل العربي + بيانات الإدخال |
"""


def generate_architectural(meta, output_dir, name):
    """Generate architectural visuals.
    
    Tries OpenAI DALL-E 3 first (production-friendly), falls back to placeholders.
    NEVER includes Arabic text in prompts to prevent broken glyphs.
    """
    facility_type = meta.get("facility_type", "Commercial Center")
    land_area = float(meta.get("land_area_sqm", 5000) or 5000)
    
    NO_TEXT = (
        " STRICTLY NO TEXT of any language. NO ARABIC, NO ENGLISH. "
        "NO LABELS, NO SIGNAGE WITH WRITING, NO LOGOS WITH TEXT. "
        "Pure visual architecture only — clean blank surfaces where signs would normally be."
    )
    
    prompts = {
        "01_Site_Plan.png": (
            f"Architectural top-down site plan of a {facility_type} facility, "
            f"plot area {land_area:.0f} square meters. "
            f"Clean technical CAD drawing on white background with navy blue lines. "
            f"Building footprints as geometric rectangles, parking lot with parking-space lines, "
            f"palm tree symbols, internal roads, pedestrian walkways, landscape zones. "
            f"Professional architectural site plan. No annotations, no labels, just shapes." + NO_TEXT,
            "1:1"
        ),
        "02_Perspective_3D.png": (
            f"Photorealistic 3D bird's-eye perspective rendering of a modern {facility_type} complex. "
            f"Contemporary minimalist Middle Eastern architecture. Beige stone and white facade. "
            f"Subtle gold metallic accents on edges. Large clear glass windows. "
            f"Manicured landscaping with palm trees, luxury cars in parking lot, "
            f"clear blue sky, golden hour sunlight casting long warm shadows. "
            f"Ultra-detailed award-winning architectural visualization. "
            f"Completely blank facade panels — no signage, no logos." + NO_TEXT,
            "16:9"
        ),
        "03_Facade_View.png": (
            f"Front facade eye-level photographic view of a modern {facility_type} building. "
            f"Contemporary architecture with clean geometric lines. "
            f"Beige stone exterior with large glass entrance and gold metal trim. "
            f"Landscaped entrance with palm trees, ambient evening LED lighting. "
            f"Professional architectural photography style. Completely blank facade — "
            f"no text, no signs, no logos visible anywhere." + NO_TEXT,
            "16:9"
        ),
        "04_Interior_Concept.png": (
            f"Interior reception lounge of a modern {facility_type}. "
            f"Spacious double-height ceiling, warm wood and stone finishes, "
            f"subtle gold metal pendant lighting, glass partitions, polished concrete floor, "
            f"comfortable lounge seating, large indoor plants. Premium minimalist design. "
            f"Architectural interior photography. Blank walls — no text artwork, "
            f"no signage." + NO_TEXT,
            "16:9"
        ),
    }
    
    for filename, (prompt, aspect) in prompts.items():
        out_path = output_dir / filename
        if not generate_image_dalle(prompt, out_path):
            create_placeholder_image(out_path, filename)


def generate_image_dalle(prompt, output_path):
    """Generate via OpenAI DALL-E 3 (production environment)."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return False
    
    try:
        import requests
        response = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt[:1000],  # DALL-E max prompt
                "n": 1,
                "size": "1792x1024",
                "quality": "standard",
            },
            timeout=120
        )
        if response.status_code == 200:
            data = response.json()
            url = data["data"][0]["url"]
            # Download
            img_response = requests.get(url, timeout=60)
            if img_response.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                return True
    except Exception as e:
        print(f"DALL-E gen failed: {e}")
    
    return False


def create_placeholder_image(output_path, filename):
    """Create a professional placeholder when AI is unavailable."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new('RGB', (1600, 900), (245, 245, 240))
        d = ImageDraw.Draw(img)
        d.rectangle([30, 30, 1569, 869], outline=(11, 61, 122), width=6)
        
        # Inner border
        d.rectangle([60, 60, 1539, 839], outline=(201, 162, 76), width=2)
        
        # Title
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 56)
            sub_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
        except:
            title_font = ImageFont.load_default()
            sub_font = ImageFont.load_default()
        
        title_map = {
            "01_Site_Plan.png": "ARCHITECTURAL SITE PLAN",
            "02_Perspective_3D.png": "3D PERSPECTIVE VIEW",
            "03_Facade_View.png": "FACADE ELEVATION",
            "04_Interior_Concept.png": "INTERIOR CONCEPT",
        }
        title = title_map.get(filename, "ARCHITECTURAL VISUAL")
        d.text((800, 380), title, anchor="mm", fill=(11, 61, 122), font=title_font)
        d.text((800, 470), "Reserved for AI-generated rendering", anchor="mm", fill=(120, 120, 120), font=sub_font)
        d.text((800, 510), "Configure OPENAI_API_KEY to enable", anchor="mm", fill=(120, 120, 120), font=sub_font)
        
        # Logo placement
        d.text((800, 700), "MUSANADA ENGINEERING CONSULTANCY", anchor="mm", fill=(201, 162, 76), font=sub_font)
        
        img.save(output_path)
    except Exception as e:
        print(f"Placeholder creation failed: {e}")


def create_placeholder_images(output_dir, meta):
    """Create all 4 placeholder images."""
    for fname in ["01_Site_Plan.png", "02_Perspective_3D.png", 
                  "03_Facade_View.png", "04_Interior_Concept.png"]:
        create_placeholder_image(output_dir / fname, fname)


# ============ MAIN ============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
