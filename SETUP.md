# 🚀 Kairos: Local Setup Guide

## 🎯 Hızlı Başlangıç

Bu guide, Kairos: The Context Keeper projesini local environment'ınızda çalıştırmanız için gerekli tüm adımları içerir.

## 📋 Gereksinimler

- **Python 3.11+** (3.12 önerilen)
- **Git**
- **8GB+ RAM** (AI modelleri için)
- **Docker** (opsiyonel, tam stack için)

## ⚡ Hızlı Kurulum (Sadece Python)

### 1. Repository'yi klonlayın
```bash
git clone https://github.com/your-username/Kairos_The_Context_Keeper.git
cd Kairos_The_Context_Keeper
```

### 2. Virtual Environment oluşturun
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### 3. Dependencies yükleyin
```bash
pip install -r requirements.txt
```

### 4. Environment dosyasını hazırlayın
```bash
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac
```

### 5. Kairos'u başlatın
```bash
# Windows
.\kairos.bat start

# Linux/Mac (bash script oluşturmanız gerekebilir)
python src/main.py
```

## 🌐 Web Interface

Kairos başlatıldıktan sonra:

- **Dashboard**: http://localhost:8000/dashboard
- **API Docs**: http://localhost:8000/docs  
- **Health Check**: http://localhost:8000/health

## 🐳 Docker ile Tam Stack (Opsiyonel)

Eğer Neo4j, Qdrant ve monitoring stack'ini de çalıştırmak istiyorsanız:

```bash
# Tüm servisleri başlat
docker-compose up -d

# Servislerin durumunu kontrol et
docker-compose ps

# Logları incele
docker-compose logs -f kairos-daemon
```

### Docker servisleri:
- **Kairos Daemon**: localhost:8000
- **Neo4j Browser**: localhost:7474 (neo4j/kairos)
- **Qdrant Dashboard**: localhost:6333
- **Prometheus**: localhost:9090
- **Grafana**: localhost:3000 (admin/kairos)

## 🛠 CLI Komutları

```bash
# Daemon'u başlat
kairos start

# System durumunu kontrol et
kairos status

# Daemon'u durdur
kairos stop

# Yeniden başlat
kairos restart

# Yardım
kairos help
```

## 🧪 Test

API endpoint'lerini test edin:

```bash
# Health check
curl http://localhost:8000/health

# Status endpoint
curl http://localhost:8000/status

# Root endpoint
curl http://localhost:8000/
```

## 🔧 Development Mode

Geliştirme için otomatik reload ile çalıştırın:

```bash
venv\Scripts\python.exe -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 Proje Yapısı

```
Kairos_The_Context_Keeper/
├── src/
│   ├── main.py              # FastAPI ana uygulama
│   ├── cli.py               # Komut satırı interface
│   ├── daemon.py            # Arka plan servisi
│   ├── agents/              # AI Agent'lar
│   └── memory/              # Context yönetimi
├── .kiro/                   # Context engineering dosyaları
├── docs/                    # Dokümantasyon
├── k8s/                     # Kubernetes manifesto'ları
├── terraform/               # Infrastructure as code
├── docker-compose.yml       # Multi-container setup
├── requirements.txt         # Python dependencies
└── kairos.bat              # Windows CLI wrapper
```

## 🚨 Troubleshooting

### Port 8000 zaten kullanımda
```bash
# Başka bir port kullan
set KAIROS_PORT=8001
python src/main.py
```

### Python not found hatası
```bash
# Virtual env'i aktif edin
venv\Scripts\activate
```

### Import hataları
```bash
# Dependencies'leri yeniden yükleyin
pip install -r requirements.txt --upgrade
```

## 🎯 Sonraki Adımlar

1. **Web Dashboard**'u ziyaret edin: http://localhost:8000/dashboard
2. **API Documentation**'u inceleyin: http://localhost:8000/docs
3. **Context engineering** dosyalarını düzenleyin: `.kiro/` klasörü
4. **Agent'ları** özelleştirin: `src/agents/` klasörü

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📞 Destek

- **GitHub Issues**: Hata raporları ve feature istekleri için
- **Email**: turtirhey@gmail.com
- **Discord**: Gelecekte eklenecek

---

🌌 **Kairos ile development sürecinizi bir üst seviyeye taşıyın!**
