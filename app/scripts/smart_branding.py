#!/usr/bin/env python3
"""
🎨 Smart Branding Generator
============================
يولّد تلقائياً:
1. Letterhead احترافي من اسم الشركة + رقم الرخصة
2. ختم رسمي دائري بالاسم والرقم
3. توقيع رقمي

كل ده **بدون الحاجة لصور جاهزة**!

Usage:
    python3 smart_branding.py <company_data.json> <output_dir>
"""

import sys
import json
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io


# ===== Colors =====
COLOR_NAVY = (12, 26, 53)
COLOR_GOLD = (201, 168, 76)
COLOR_GOLD_LIGHT = (240, 192, 64)
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 116, 139)
COLOR_RED = (220, 38, 38)
COLOR_BLUE = (37, 99, 235)


def find_arabic_font():
    """البحث عن خط عربي متاح"""
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf",
    ]
    for f in candidates:
        if Path(f).exists():
            return f
    return None


def create_letterhead_logo(
    company_ar: str,
    company_en: str,
    output_path: str,
    color_primary=COLOR_NAVY,
    color_accent=COLOR_GOLD,
    size=(800, 200),
):
    """
    يصنع Letterhead Logo احترافي:
    - شكل هندسي بسيط (مساطر + قوس)
    - اسم الشركة بالعربي (كبير)
    - اسم الشركة بالإنجليزي (تحت)
    """
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to load fonts
    font_path = find_arabic_font()
    try:
        font_ar = ImageFont.truetype(font_path, 36) if font_path else ImageFont.load_default()
        font_en = ImageFont.truetype(font_path, 18) if font_path else ImageFont.load_default()
        font_small = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
    except Exception:
        font_ar = ImageFont.load_default()
        font_en = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # Draw a geometric mark on the left (simple building/columns)
    mark_x = 30
    mark_y = 40
    mark_size = 120
    
    # Background circle
    draw.ellipse(
        [(mark_x, mark_y), (mark_x + mark_size, mark_y + mark_size)],
        fill=color_primary,
    )
    
    # Inner gold ring
    ring_offset = 8
    draw.ellipse(
        [(mark_x + ring_offset, mark_y + ring_offset),
         (mark_x + mark_size - ring_offset, mark_y + mark_size - ring_offset)],
        outline=color_accent,
        width=3,
    )
    
    # Vertical columns (building lines)
    col_w = 8
    col_x_base = mark_x + 30
    for i, h_pct in enumerate([0.55, 0.75, 0.95, 0.75, 0.55]):
        col_h = int(60 * h_pct)
        col_x = col_x_base + i * 12
        col_y = mark_y + 80 - col_h
        draw.rectangle(
            [col_x, col_y, col_x + col_w, mark_y + 80],
            fill=color_accent,
        )
    
    # Arabic name (large)
    text_x = mark_x + mark_size + 30
    draw.text((text_x, 50), company_ar, font=font_ar, fill=color_primary)
    
    # English name (small below)
    draw.text((text_x, 105), company_en, font=font_en, fill=color_accent)
    
    # Decorative line under names
    line_y = 135
    draw.line(
        [(text_x, line_y), (text_x + 400, line_y)],
        fill=color_accent,
        width=2,
    )
    draw.line(
        [(text_x, line_y + 4), (text_x + 200, line_y + 4)],
        fill=color_primary,
        width=1,
    )
    
    img.save(output_path, "PNG")
    print(f"✅ Logo saved: {output_path}")
    return output_path


def create_official_stamp(
    company_ar: str,
    company_en: str,
    license_no: str,
    output_path: str,
    color=COLOR_RED,
    size=300,
):
    """
    يصنع ختم رسمي دائري:
    - دائرتين متحدتي المركز
    - الاسم بالعربي على المحيط الخارجي
    - الاسم بالإنجليزي على المحيط الداخلي
    - رقم الرخصة في المنتصف
    """
    canvas_size = size + 40
    img = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    cx, cy = canvas_size // 2, canvas_size // 2
    outer_r = size // 2
    middle_r = outer_r - 25
    inner_r = outer_r - 50
    
    # Outer circle
    draw.ellipse(
        [(cx - outer_r, cy - outer_r), (cx + outer_r, cy + outer_r)],
        outline=color,
        width=4,
    )
    
    # Middle circle
    draw.ellipse(
        [(cx - middle_r, cy - middle_r), (cx + middle_r, cy + middle_r)],
        outline=color,
        width=2,
    )
    
    # Inner circle (for license number)
    draw.ellipse(
        [(cx - inner_r, cy - inner_r), (cx + inner_r, cy + inner_r)],
        outline=color,
        width=1,
    )
    
    # Decorative stars
    for angle in [0, 90, 180, 270]:
        rad = math.radians(angle)
        sx = cx + int((middle_r - 12) * math.cos(rad))
        sy = cy + int((middle_r - 12) * math.sin(rad))
        # Draw small star (just a + sign)
        draw.line([(sx - 4, sy), (sx + 4, sy)], fill=color, width=2)
        draw.line([(sx, sy - 4), (sx, sy + 4)], fill=color, width=2)
    
    # License number in center
    font_path = find_arabic_font()
    try:
        font_center_big = ImageFont.truetype(font_path, 22) if font_path else ImageFont.load_default()
        font_center_small = ImageFont.truetype(font_path, 14) if font_path else ImageFont.load_default()
        font_arc = ImageFont.truetype(font_path, 16) if font_path else ImageFont.load_default()
    except Exception:
        font_center_big = ImageFont.load_default()
        font_center_small = ImageFont.load_default()
        font_arc = ImageFont.load_default()
    
    # Center text
    bbox = draw.textbbox((0, 0), license_no, font=font_center_big)
    text_w = bbox[2] - bbox[0]
    draw.text(
        (cx - text_w // 2, cy - 25),
        license_no,
        font=font_center_big,
        fill=color,
    )
    
    # Sub label
    sub_text = "رخصة"
    bbox2 = draw.textbbox((0, 0), sub_text, font=font_center_small)
    sub_w = bbox2[2] - bbox2[0]
    draw.text(
        (cx - sub_w // 2, cy + 5),
        sub_text,
        font=font_center_small,
        fill=color,
    )
    
    # Year
    from datetime import datetime
    year_str = str(datetime.now().year)
    bbox3 = draw.textbbox((0, 0), year_str, font=font_center_small)
    yr_w = bbox3[2] - bbox3[0]
    draw.text(
        (cx - yr_w // 2, cy + 22),
        year_str,
        font=font_center_small,
        fill=color,
    )
    
    # Curved text along outer circle (simplified: just show name in middle)
    # PIL doesn't easily support curved text, so we'll add it straight at top and bottom
    # Top text (Arabic)
    top_text = company_ar[:35] if len(company_ar) > 35 else company_ar
    bbox_top = draw.textbbox((0, 0), top_text, font=font_arc)
    top_w = bbox_top[2] - bbox_top[0]
    draw.text(
        (cx - top_w // 2, cy - middle_r + 5),
        top_text,
        font=font_arc,
        fill=color,
    )
    
    # Bottom text (English)
    bottom_text = company_en[:35] if len(company_en) > 35 else company_en
    bbox_bot = draw.textbbox((0, 0), bottom_text, font=font_arc)
    bot_w = bbox_bot[2] - bbox_bot[0]
    draw.text(
        (cx - bot_w // 2, cy + middle_r - 20),
        bottom_text,
        font=font_arc,
        fill=color,
    )
    
    img.save(output_path, "PNG")
    print(f"✅ Stamp saved: {output_path}")
    return output_path


def create_signature(
    name: str,
    output_path: str,
    color=COLOR_BLUE,
    size=(400, 150),
):
    """
    يصنع توقيع رقمي بشكل خط متعرج
    """
    img = Image.new("RGBA", size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw a stylized signature (zigzag with curves)
    import random
    random.seed(sum(ord(c) for c in name))
    
    # Main loop  
    points = []
    x = 30
    y = 75
    
    for i in range(60):
        # Random vertical movement
        y_off = random.randint(-30, 30) if i % 3 == 0 else random.randint(-10, 10)
        next_x = x + random.randint(4, 10)
        next_y = y + y_off
        
        # Keep within bounds
        next_y = max(20, min(130, next_y))
        next_x = min(370, next_x)
        
        points.append((next_x, next_y))
        x = next_x
    
    # Draw the signature line
    for i in range(len(points) - 1):
        draw.line([points[i], points[i+1]], fill=color, width=3)
    
    # Add an underline flourish
    draw.line([(30, 130), (370, 135)], fill=color, width=2)
    
    img.save(output_path, "PNG")
    print(f"✅ Signature saved: {output_path}")
    return output_path


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 smart_branding.py <company_data.json> <output_dir>")
        sys.exit(1)
    
    company_file = Path(sys.argv[1])
    output_dir = Path(sys.argv[2])
    output_dir.mkdir(parents=True, exist_ok=True)
    
    company = json.loads(company_file.read_text(encoding="utf-8"))
    
    company_ar = company.get("company_name_ar") or company.get("legal_name_ar") or "شركة الاستشارات"
    company_en = company.get("company_name_en") or company.get("legal_name_en") or "Engineering Consultancy"
    license_no = company.get("license_no") or company.get("license_number") or "CN-XXXXXX"
    director = company.get("authorized_signatory") or company.get("director_name") or "المدير العام"
    
    # Generate all assets
    logo_path = output_dir / "logo_generated.png"
    stamp_path = output_dir / "stamp_generated.png"
    sig_path = output_dir / "signature_generated.png"
    
    create_letterhead_logo(company_ar, company_en, str(logo_path))
    create_official_stamp(company_ar, company_en, license_no, str(stamp_path))
    create_signature(director, str(sig_path))
    
    # Output manifest
    manifest = {
        "company_ar": company_ar,
        "company_en": company_en,
        "license_no": license_no,
        "assets": {
            "logo": str(logo_path),
            "stamp": str(stamp_path),
            "signature": str(sig_path),
        }
    }
    
    (output_dir / "branding_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    
    print(f"\n✅ All branding assets generated in: {output_dir}")


if __name__ == "__main__":
    main()
