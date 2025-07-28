# Warp Terminal Güvenlik Entegrasyonu

Bu araçlar, Warp terminal'in Secret Redaction özelliğini yönetmek ve API anahtarlarını korumak için geliştirilmiştir.

## 🛡️ Warp Secret Redaction Nedir?

Warp'ın Secret Redaction özelliği, terminal çıktısında API anahtarları, token'lar ve diğer hassas bilgileri otomatik olarak maskeleyen bir güvenlik katmanıdır. Bu özellik sayesinde:

- OpenAI API anahtarları
- AWS erişim anahtarları
- GitHub PAT'leri
- Bearer token'lar
- Ve diğer hassas bilgiler

Terminal çıktısında `••••REDACTED••••` şeklinde maskelenir ve güvenli bir şekilde korunur.

## 🚀 Kurulum ve Kullanım

### 1. Warp Terminal Kurulumu

Eğer Warp terminal kurulu değilse, [warp.dev](https://www.warp.dev/) adresinden indirebilirsiniz.

Windows için kurulum:
```
winget install Warp.Warp
```

### 2. Secret Redaction Yönetimi

`warp-secret-redaction.ps1` scripti ile Secret Redaction özelliğini yönetebilirsiniz:

```powershell
# Durumu kontrol et
.\warp-secret-redaction.ps1 -Action status

# Secret Redaction'ı etkinleştir
.\warp-secret-redaction.ps1 -Action enable

# Secret Redaction'ı devre dışı bırak
.\warp-secret-redaction.ps1 -Action disable

# Test et
.\warp-secret-redaction.ps1 -Action test

# Warp'ı başlat
.\warp-secret-redaction.ps1 -Action start
```

### 3. API Anahtarı Koruma ve Tarama

`warp-api-key-protection.ps1` scripti ile API anahtarlarını tarayabilir ve koruyabilirsiniz:

```powershell
# Dosya veya dizini API anahtarları için tara
.\warp-api-key-protection.ps1 -Action scan -FilePath C:\Projeler

# Koruma önerilerini görüntüle ve Secret Redaction'ı etkinleştir
.\warp-api-key-protection.ps1 -Action protect

# Warp ayarlarını görüntüle
.\warp-api-key-protection.ps1 -Action settings

# Belirli bir dosyayı analiz et
.\warp-api-key-protection.ps1 -Action analyze -FilePath C:\Projeler\config.json
```

## 📋 Özellikler

### Secret Redaction Yönetimi
- Secret Redaction durumunu kontrol etme
- Secret Redaction'ı etkinleştirme/devre dışı bırakma
- Test etme ve örnek API anahtarlarını maskeleme

### API Anahtarı Koruma
- Dosya ve dizinleri API anahtarları için tarama
- Bulunan API anahtarlarını maskeleme ve raporlama
- Koruma önerileri sunma
- Warp ayarlarını görüntüleme

## 🔒 Desteklenen API Anahtarı Türleri

- OpenAI API Key (`sk-...`)
- Google API Key (`AIza...`)
- AWS Access Key ID (`AKIA...`)
- GitHub Personal Access Token (`ghp_...`)
- Slack Bot Token (`xoxb-...`)
- Google OAuth Token (`ya29....`)
- UUID Desenleri
- Bearer Token'lar
- Basic Auth Token'lar

## ⚠️ Önemli Notlar

1. Bu araçlar, Warp terminal'in Secret Redaction özelliğini yönetmek için geliştirilmiştir.
2. Secret Redaction, terminal çıktısında hassas bilgileri maskeler, ancak dosyalardaki hassas bilgileri değiştirmez.
3. API anahtarlarını her zaman güvenli bir şekilde saklayın ve `.env` dosyalarında tutun.
4. `.gitignore` dosyanıza hassas bilgi içeren dosyaları ekleyin.
5. Düzenli olarak kod tabanınızı API anahtarları için tarayın.

## 🔄 Warp ve Kiro IDE Entegrasyonu

Warp terminal, Kiro IDE ile birlikte kullanıldığında güçlü bir geliştirme ortamı sunar:

1. Warp'ın Secret Redaction özelliği ile hassas bilgiler korunur
2. Kiro IDE'nin API Key Sniffer MCP'si ile kod tabanı taranır
3. İki sistem birlikte çalışarak tam koruma sağlar

## 📚 Kaynaklar

- [Warp Terminal](https://www.warp.dev/)
- [Warp Dokümantasyonu](https://docs.warp.dev/)
- [Secret Redaction Hakkında](https://docs.warp.dev/features/secret-redaction)