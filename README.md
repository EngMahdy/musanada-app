# مساندة للاستشارات الهندسية | Musanada Engineering Consultancy

> منصة AI لتجهيز ملفات مناقصات الإمارات (DMT + ADIO) — تطبيق ويب كامل.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

---

## ⚡ ما الذي يفعله التطبيق؟

يستقبل ملف المناقصة + بيانات الشركة + اللوجو والختم والتوقيع، ويُخرج خلال دقائق:

1. **8 نماذج DOCX/PDF** (Form A, D, E, G, H, I × 3) معبّأة وجاهزة للتوقيع
2. **نموذج Excel مالي** بـ 10 شيتات (Cover, Assumptions, CAPEX, Revenue, OPEX, P&L, Cash Flow, 25Y Summary, KPIs, Sensitivity)
3. **مخطط موقعي** (Site Plan) + **3 منظورات 3D** للمشروع
4. **تحليل عربي تفصيلي** للمناقصة
5. **حزمة ZIP نهائية** جاهزة للرفع على بوابة DMT/ADIO

---

## 🚀 النشر على Render (مجاناً)

### الطريقة 1: Auto Deploy

1. Fork هذا الـrepo على GitHub
2. اذهب لـ [Render Dashboard](https://dashboard.render.com)
3. اضغط **New +** → **Blueprint**
4. أوصِل GitHub repo
5. Render يقرأ `render.yaml` تلقائياً وينشر التطبيق
6. الـURL هيكون: `https://musanada.onrender.com`

### الطريقة 2: Manual Setup

1. اذهب لـ [Render Dashboard](https://dashboard.render.com) → **New Web Service**
2. اختر GitHub repo
3. Settings:
   - **Runtime:** Docker
   - **Dockerfile Path:** `./Dockerfile`
   - **Plan:** Free
   - **Health Check Path:** `/health`
4. **Environment Variables (اختياري):**
   - `OPENAI_API_KEY` = مفتاحك من OpenAI (لتوليد الصور المعمارية الفعلية)
5. اضغط **Create Web Service**

---

## 🔑 إعداد OpenAI API Key (للصور المعمارية)

التطبيق يستخدم DALL-E 3 لتوليد المخططات والمناظير. بدون مفتاح، يستخدم placeholder images.

1. اذهب لـ [OpenAI Platform](https://platform.openai.com/api-keys)
2. اعمل API Key جديد
3. في Render → Web Service → **Environment** → أضف:
   - `OPENAI_API_KEY` = `sk-...`
4. **التكلفة:** ~$0.04 لكل صورة (4 صور × $0.04 = $0.16 لكل مناقصة)

---

## 🛠️ التشغيل المحلي

```bash
# Clone
git clone https://github.com/YOUR_USERNAME/musanada-app.git
cd musanada-app

# Install dependencies
pip install -r requirements.txt

# Install system deps (Ubuntu/Debian)
sudo apt-get install poppler-utils p7zip-full fonts-noto libreoffice

# Run
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

افتح `http://localhost:8080` في المتصفح.

### تشغيل بـ Docker

```bash
docker build -t musanada .
docker run -p 8080:8080 -e OPENAI_API_KEY=$OPENAI_API_KEY musanada
```

---

## 📁 هيكل المشروع

```
musanada-deploy/
├── app/
│   ├── main.py              # FastAPI backend
│   ├── templates/
│   │   └── index.html       # Frontend (Arabic RTL)
│   ├── brand/               # Logo, favicon
│   ├── scripts/             # Tender processing scripts
│   │   ├── extract_tender.py
│   │   ├── build_analysis.py
│   │   ├── generate_adio_forms.py
│   │   ├── financial_model.py
│   │   └── ...
│   └── data/                # Reference data
├── Dockerfile               # Container definition
├── render.yaml              # Render blueprint
├── Procfile                 # Heroku-style start cmd
├── requirements.txt         # Python dependencies
└── README.md
```

---

## 🔧 API Endpoints

| Method | Path | الوصف |
|--------|------|------|
| `GET` | `/` | الواجهة الرئيسية (Arabic UI) |
| `GET` | `/health` | Health check |
| `POST` | `/api/process` | معالجة مناقصة (multipart form) |
| `GET` | `/outputs/{job_id}/...` | تنزيل الملفات المُولّدة |

### مثال curl:

```bash
curl -X POST https://your-app.onrender.com/api/process \
  -F "tender_file=@tender.zip" \
  -F "company_legal_name=Your Company LLC" \
  -F "legal_form=LLC" \
  -F "establishment_date=2010-01-01" \
  -F "nature_of_business=Construction" \
  -F "hq_address=Abu Dhabi" \
  -F "company_email=info@yourco.ae" \
  -F "trade_license_no=CN-1234567" \
  -F "authorized_signatory_name=John Doe" \
  -F "authorized_signatory_title=CEO" \
  -F "logo=@logo.png" \
  -F "signature=@signature.png" \
  -F "stamp=@stamp.png"
```

---

## 🎨 لماذا لا توجد كتابة عربية في الصور المعمارية؟

نماذج توليد الصور (DALL-E, Midjourney, Stable Diffusion) **غير قادرة على رسم النصوص العربية بشكل صحيح**. تطلع كأشكال مشوّهة. لذلك التطبيق:

- ✅ يولّد صور معمارية احترافية **بدون أي نص**
- ✅ Facade panels فاضية يمكنك تركيب لوجو شركتك عليها بالـPhotoshop لاحقاً
- ✅ المخططات نظيفة بـCAD-style خطوط فقط

---

## ⚠️ ملاحظات مهمة

- **Render Free Plan:** التطبيق ينام بعد 15 دقيقة من عدم النشاط، يستيقظ في 30 ثانية عند أول طلب
- **Outputs:** تُحفظ في `/tmp` (ephemeral) - تختفي عند restart السيرفر، لذلك نزّل النتائج فوراً
- **حد الـUpload:** 100MB لـZIP المناقصة
- **زمن المعالجة:** 1-3 دقائق لكل مناقصة (يعتمد على عدد المناقصات داخل الـZIP)

---

## 📞 الدعم

- **Issues:** أنشئ issue على GitHub
- **Email:** info@musanada.ae

---

## 📜 الترخيص

Proprietary — مساندة للاستشارات الهندسية © 2026
