# MCP Problemleri ve Çözümleri

## 🔍 Tespit Edilen Ana Problemler

### 1. ❌ UVX Komutu Bulunamıyor
**Problem**: 7 MCP server `uvx` komutunu kullanıyor ama sistem PATH'inde yok
- filesystem, sqlite, git, github, brave-search, memory, fetch

**Çözüm**: UVX kurulumu gerekli
```bash
# Python uv paket yöneticisini kur
pip install uv
# uvx otomatik olarak gelir
```

### 2. ❌ Boto3 Import Hatası
**Problem**: `cannot import name 'CRT_SUPPORTED_AUTH_TYPES' from 'botocore.crt'`
**Çözüm**: Boto3/botocore versiyonlarını güncelle
```bash
pip install --upgrade boto3 botocore
```

### 3. ⚠️ API Anahtarları Eksik
**Problem**: Tüm önemli API anahtarları environment'da yok
- GOOGLE_API_KEY
- BRAVE_SEARCH_API_KEY  
- AWS_ACCESS_KEY_ID
- AWS_SECRET_ACCESS_KEY
- OPENAI_API_KEY
- ANTHROPIC_API_KEY

### 4. ⚠️ Network Bağlantı Sorunları
**Problem**: httpbin.org timeout veriyor
**Çözüm**: Network/proxy ayarlarını kontrol et

### 5. ⚠️ PYTHONIOENCODING Eksik
**Problem**: UTF-8 encoding sorunları olabilir
**Çözüm**: Environment variable ekle

## 🛠️ Hızlı Çözüm Planı

### Adım 1: UVX Kurulumu
```bash
pip install uv
```

### Adım 2: Boto3 Düzeltme
```bash
pip install --upgrade boto3 botocore
```

### Adım 3: Environment Variables
```bash
# .env dosyasına ekle
PYTHONIOENCODING=utf-8
GOOGLE_API_KEY=your_key_here
BRAVE_SEARCH_API_KEY=your_key_here
```

### Adım 4: Requirements.txt Güncelleme
```txt
# Eksik paketler ekle
uv>=0.1.0
```

### Adım 5: Sorunlu Serverları Geçici Disable Et
```json
{
  "disabled": true
}
```

## 📊 Server Durumu Özeti

| Server             | Durum           | Problem        | Çözüm |
| ------------------ | --------------- | -------------- | ----- |
| kiro-tools         | ✅ OK            | -              | -     |
| test-mcp           | ✅ OK            | -              | -     |
| api-key-sniffer    | ✅ OK            | -              | -     |
| context-graph      | ✅ OK            | -              | -     |
| filesystem         | ❌ uvx yok       | UVX kur        |       |
| sqlite             | ❌ uvx yok       | UVX kur        |       |
| git                | ❌ uvx yok       | UVX kur        |       |
| aws-bedrock        | ❌ boto3         | Boto3 güncelle |       |
| browser-automation | ⚠️ Test edilmedi | API keys       |       |
| real-browser       | ⚠️ Test edilmedi | API keys       |       |

## 🎯 Öncelik Sırası

1. **Yüksek Öncelik**: UVX kurulumu (7 server etkileniyor)
2. **Orta Öncelik**: Boto3 düzeltme (AWS entegrasyonu için)
3. **Düşük Öncelik**: API anahtarları (özellik bazlı)

## 🚀 Otomatik Düzeltme Scripti

Tüm problemleri otomatik çözen script oluşturalım.