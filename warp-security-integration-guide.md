# Warp Terminal Güvenlik Entegrasyonu Rehberi

## 🛡️ Giriş

Bu rehber, Warp terminal'in Secret Redaction özelliğini Kiro IDE ile entegre ederek güçlü bir API anahtarı koruma sistemi oluşturmayı anlatır. Bu entegrasyon, terminal çıktısında hassas bilgilerin otomatik maskelenmesini ve kod tabanının düzenli olarak API anahtarları için taranmasını sağlar.

## 📋 Adım Adım Kurulum

### 1. Warp Terminal Kurulumu

Eğer Warp terminal kurulu değilse:

1. [warp.dev](https://www.warp.dev/) adresinden indirin veya
2. Windows için: `winget install Warp.Warp` komutunu çalıştırın

### 2. Güvenlik Entegrasyonu Kurulumu

Tüm güvenlik özelliklerini tek adımda kurmak için:

```powershell
.\setup-warp-security.ps1
```

Bu script şunları yapar:
- Warp terminal'in kurulu olup olmadığını kontrol eder
- Secret Redaction'ı yapılandırır
- API Key Sniffer entegrasyonunu kurar
- Test taraması yapar
- Warp terminal'i başlatır

### 3. Manuel Kurulum (İsteğe Bağlı)

Adım adım manuel kurulum yapmak isterseniz:

1. **Secret Redaction Durumunu Kontrol Edin**
   ```powershell
   .\warp-secret-redaction.ps1 -Action status
   ```

2. **Secret Redaction'ı Etkinleştirin**
   ```powershell
   .\warp-secret-redaction.ps1 -Action enable
   ```

3. **API Key Sniffer Entegrasyonunu Kurun**
   ```powershell
   .\warp-api-key-sniffer-integration.ps1 -Action setup -TargetPath . -OutputDir api_key_sniffer_data
   ```

4. **Test Taraması Yapın**
   ```powershell
   .\warp-api-key-protection.ps1 -Action scan -FilePath . -OutputPath api_key_sniffer_data\test_scan.json
   ```

5. **Warp Terminal'i Başlatın**
   ```powershell
   .\warp-secret-redaction.ps1 -Action start
   ```

## 🔍 Güvenlik Taraması ve İzleme

### Tek Seferlik Tarama

Kod tabanınızı API anahtarları için taramak için:

```powershell
.\warp-api-key-protection.ps1 -Action scan -FilePath C:\Projeler
```

### Düzenli İzleme

Kod tabanınızı düzenli olarak taramak için izleme modunu kullanın:

```powershell
.\warp-api-key-sniffer-integration.ps1 -Action monitor -TargetPath .
```

Bu komut, kod tabanınızı saatlik olarak tarar ve sonuçları raporlar.

### Rapor Oluşturma

En son tarama sonuçlarına göre rapor oluşturmak için:

```powershell
.\warp-api-key-sniffer-integration.ps1 -Action report
```

## 🔧 Sorun Giderme

### MCP Sunucusu Sorunları

MCP sunucularında sorun yaşıyorsanız:

```powershell
python mcp-fix-updated.py
```

Bu script, MCP yapılandırmasını kontrol eder, sunucu yollarını düzeltir ve test sunucusu oluşturur.

### Secret Redaction Sorunları

Secret Redaction çalışmıyorsa:

1. Warp ayarlarını kontrol edin:
   ```powershell
   .\warp-api-key-protection.ps1 -Action settings
   ```

2. Secret Redaction'ı yeniden etkinleştirin:
   ```powershell
   .\warp-secret-redaction.ps1 -Action enable
   ```

3. Test edin:
   ```powershell
   .\warp-secret-redaction.ps1 -Action test
   ```

## 📊 Güvenlik Raporları

Tarama sonuçları ve raporlar `api_key_sniffer_data` dizininde saklanır:

- `initial_scan.json` - İlk tarama sonuçları
- `scan_[timestamp].json` - Tarama sonuçları
- `report_[timestamp].md` - Markdown formatında raporlar

Raporlar şunları içerir:
- Taranan dosya sayısı
- Bulunan API anahtarı sayısı
- Yüksek riskli anahtar sayısı
- Detaylı bulgular
- Güvenlik önerileri
- Warp Secret Redaction durumu

## 🔒 En İyi Güvenlik Uygulamaları

1. **API Anahtarlarını Güvenli Saklama**
   - API anahtarlarını `.env` dosyalarında saklayın
   - `.gitignore` dosyanıza `.env` ve diğer hassas dosyaları ekleyin

2. **Düzenli Tarama**
   - Kod tabanınızı düzenli olarak API anahtarları için tarayın
   - İzleme modunu kullanarak otomatik tarama yapın

3. **Git Hook'ları**
   - Commit öncesi API anahtarlarını taramak için git hook'ları kullanın
   - Hassas bilgi içeren commit'leri engelleyin

4. **Secret Redaction**
   - Warp Secret Redaction özelliğini her zaman etkin tutun
   - Terminal çıktısında hassas bilgilerin maskelendiğinden emin olun

5. **Güvenlik Raporları**
   - Güvenlik raporlarını düzenli olarak inceleyin
   - Bulunan sorunları hemen çözün

## 🔄 Kiro IDE Entegrasyonu

Warp terminal ve Kiro IDE entegrasyonu şu avantajları sağlar:

- Terminal çıktısında hassas bilgilerin otomatik maskelenmesi
- Kod tabanının düzenli olarak API anahtarları için taranması
- Güvenlik raporları ve önerileri
- Warp'ın modern terminal özellikleri ile Kiro IDE'nin güçlü geliştirme ortamının birleşimi

## 📚 Kaynaklar

- [Warp Terminal](https://www.warp.dev/)
- [Warp Dokümantasyonu](https://docs.warp.dev/)
- [Secret Redaction Hakkında](https://docs.warp.dev/features/secret-redaction)
- [API Key Güvenliği Hakkında](https://docs.warp.dev/features/secret-redaction)