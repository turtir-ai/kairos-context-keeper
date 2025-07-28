# Sprint 4: Otonom Yetenekleri Aktive Etme ve Sistemi Sağlamlaştırma

**Sprint Hedefi:** Kairos'un altyapısı ile fonksiyonelliği arasındaki boşluğu kapatmak. Mock (sahte) implementasyonları, gerçek dünyada çalışan, veri işleyen, öğrenen ve kalıcı hafızaya sahip agent'lara dönüştürmek. 

---

## Faz 1: Agent'ları "Canlandırma" ve Fonksiyonel Hale Getirme

**Amaç:** Agent'ların sahte veri üretmek yerine, gerçek dünyadan veri toplayıp, LLM'lerle analiz edip, anlamlı çıktılar üretmesini sağlamak.

### Görev 1.1: ResearchAgent'ı Gerçek Bir Araştırmacıya Dönüştürmek

* **Hedef:** `ResearchAgent`'ın internetten ve dosyalardan aktif olarak bilgi toplayabilmesi.
* **Teknik Adımlar:**
  1. **Harici Araç Entegrasyonu:**
     * Web araştırmaları için entegrasyonunu tamamla.
     * PDF ve metin dosyalarını işlemek.
  2. **`research` Metodunu Yeniden Yaz:**
     * Araştırma planı oluşturması.
     * Toplanan bilgiyi geçici saklamalı.
  3. **LLM ile Sentezleme:** Ham bilgiyi özet ve çıkarımlar yapmak için kullan.
  4. **Sonuçları Atomize Etme:** "Kairos Atomu" formatında yapılandır.
* **Başarı Kriteri:** Bilgi toplayıp özet üretip hafızaya kaydetmesi.

### Görev 1.2: GuardianAgent'ı Gerçek Bir Denetçiye Dönüştürmek

* **Hedef:** `GuardianAgent`'ın, projenin "Anayasası"na göre derinlemesine kod ve çıktı denetimi yapabilmesi.
* **Teknik Adımlar:**
  1. **Anayasa Entegrasyonu:** Kodlama standartları tanımla.
  2. **Statik Kod Analizi:** `ruff` veya `pylint` gibi linter kullan.
  3. **LLM Destekli Mantıksal Denetim:** Daha karmaşık kontroller için LLM kullan.
* **Başarı Kriteri:** Anayasayı ihlal eden bir kod bulması.

---

## Faz 2: Gerçek Zamanlı Veri Akışını ve Kalıcılığı Tamamlama

**Amaç:** Agent'ların ürettiği gerçek sonuçların hafıza katmanına kalıcı şekilde kaydedilmesi.

### Görev 2.1: WebSocket Yöneticisi Entegrasyon Hatasını Giderme

* **Hedef:** WebSocket yöneticisini `agent_coordinator` ile doğru bir şekilde entegre etmek.
* **Teknik Adımlar:**
  1. WebSocketManager'ı Coordinator'a tanımla.
* **Başarı Kriteri:** `None` hatası vermemesi.

### Görev 2.2: Görev Sonuçlarını Hafızaya Kalıcı Olarak Yazma

* **Hedef:** Görev sonuçlarının Neo4j ve Qdrant'a kaydedilmesi.
* **Teknik Adımlar:**
  1. Sonuçları hafızaya ekleme işlevselliğini uygula.
* **Başarı Kriteri:** Sonuçların kalıcı olarak saklanması.

### Görev 2.3: Frontend'de Global Durum Yönetimi

* **Hedef:** Arayüz bileşenlerinin canlı verilerle güncellenmesi.
* **Teknik Adımlar:**
  1. React Context API kullanarak global durum yönetimini uygula.
* **Başarı Kriteri:** Anında güncelleme.

---

## Faz 3: Sistemi Sağlamlaştırma

**Amaç:** Projeyi dış tehditlere karşı korumak ve güvenilir bir test altyapısı kurmak.

### Görev 3.1: Temel Güvenlik Katmanı Ekleme

* **Hedef:** API ve WebSocket endpoint'lerini korumak.
* **Teknik Adımlar:**
  1. API anahtarı ile güvenlik sağla.
* **Başarı Kriteri:** Yetkisiz erişim engellenmesi.

### Görev 3.2: Test Altyapısını Kurma

* **Hedef:** Otomatik test altyapısını kurmak.
* **Teknik Adımlar:**
  1. `pytest` ile testler oluştur.
* **Başarı Kriteri:** Başarılı test geçişi.

---

Bu sprint planı, projenin mevcut durumundaki en kritik eksikleri gidererek onu vizyonumuza bir adım daha yaklaştıracak ve bir sonraki "Otonom Öğrenme" sprinti için sağlam bir zemin hazırlayacaktır.
