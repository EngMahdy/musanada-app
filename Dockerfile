FROM python:3.11-slim

# System dependencies for tender processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    p7zip-full \
    fonts-noto \
    fonts-dejavu \
    libreoffice \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/

# Create writable dirs
RUN mkdir -p /tmp/musanada_outputs && chmod 777 /tmp/musanada_outputs

# Environment
ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV OUTPUTS_DIR=/tmp/musanada_outputs

EXPOSE 8080

# Run via uvicorn
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
