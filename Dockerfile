FROM python:3.11-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıklarını kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodunu kopyala
COPY . .

# Gerekli dizinleri oluştur
RUN mkdir -p /app/data/vector_db \
    /app/data/graph_db \
    /app/logs

# Ortam değişkenlerini ayarla
ENV PYTHONPATH=/app \
    VECTOR_DB_PATH=/app/data/vector_db \
    GRAPH_DB_PATH=/app/data/graph_db \
    LOG_PATH=/app/logs

# Sağlık kontrolü
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Uygulamayı çalıştır
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"] 