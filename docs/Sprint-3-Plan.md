# Sprint 3: Otonom Zeka ve Kurumsal Yetenekler

**Sprint Hedefi:** Kairos'u, temel bir prototipten, kendi kendine öğrenen, çok kullanıcılı ve kurumsal düzeyde güvenilirliğe sahip, üretime hazır bir AI geliştirme süpervizörüne dönüştürmek.

**Sprint Süresi:** 3 Hafta  
**Başlangıç Tarihi:** [TBD]  
**Bitiş Tarihi:** [TBD]

---

## 🎯 Sprint Özeti

Bu sprint'te Kairos'un dört temel alanda geliştirilmesi hedeflenmektedir:
1. **Sistemin Bütünlüğünün Sağlanması** - Sprint 2'nin tamamlanması
2. **Gelişmiş AI Entegrasyonu** - Akıllı model seçimi ve öğrenme
3. **Kurumsal Güvenlik** - Çok kullanıcılı ve güvenli erişim
4. **Performans Optimizasyonu** - Ölçeklenebilir mimari

---

## 📅 Haftalık Plan

### **Hafta 1: Temellerin Sağlamlaştırılması**

Sprint 2'nin eksik kalan bileşenlerinin tamamlanması ve sistem bütünlüğünün sağlanması.

#### **🔧 Görev 1.1: Neo4j & Qdrant Canlı Entegrasyonu**

**Öncelik:** 🔴 Yüksek  
**Tahmin:** 2 gün  
**Sorumlu:** Backend Developer  

**Hedef:** `MemoryManager`'ın Docker üzerinde çalışan canlı veritabanlarına veri yazıp okumasını sağlamak.

**Teknik Gereksinimler:**
- [ ] `docker-compose.yml` servis ayarlarını doğrula
  - [ ] Neo4j ports ve volumes kontrolü
  - [ ] Qdrant konfigürasyon kontrolü
- [ ] `.env` dosyasına veritabanı bağlantı değişkenlerini ekle
  ```bash
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USER=neo4j
  NEO4J_PASSWORD=password
  QDRANT_HOST=localhost:6333
  ```
- [ ] `src/memory/memory_manager.py` güncelle
  - [ ] Ortam değişkenlerinden veritabanı istemcilerini başlat
  - [ ] Gerçek zamanlı veri yazma fonksiyonları
- [ ] Birim testleri yaz (`pytest`)
  - [ ] `test_neo4j_connection()`
  - [ ] `test_qdrant_connection()`
  - [ ] `test_memory_persistence()`

**Başarı Kriteri:** ✅ Görev çalıştırıldığında, "Kairos Atomu" Neo4j Browser'da ve embedding Qdrant UI'da anında görünür.

---

#### **🧪 Görev 1.2: Uçtan Uca Test Sistemi**

**Öncelik:** 🔴 Yüksek  
**Tahmin:** 3 gün  
**Sorumlu:** Full-Stack Developer  

**Hedef:** CLI -> Daemon -> Orchestrator -> Agent -> Memory -> UI zincirinin hatasız çalıştığını garanti etmek.

**Teknik Gereksinimler:**
- [ ] `tests/test_e2e_workflow.py` oluştur
- [ ] Otomatik test senaryosu geliştir:
  - [ ] `kairos start` ile sistem başlatma
  - [ ] `/api/orchestration/tasks` endpoint'ine POST request
  - [ ] Görev durumu takibi (`pending` -> `running` -> `completed`)
  - [ ] Hafıza sorgusu doğrulaması
  - [ ] WebSocket kommunikasyon testi
- [ ] Playwright/Selenium ile UI testleri
- [ ] Test kapsamı (coverage) analizi

**Başarı Kriteri:** ✅ E2E testler manual müdahale olmadan başarılı, test kapsamı >70%.

---

#### **⚡ Görev 1.3: Performans Optimizasyonu**

**Öncelik:** 🟡 Orta  
**Tahmin:** 2 gün  
**Sorumlu:** Backend Developer  

**Hedef:** Sistem darboğazlarını tespit edip gidermek.

**Teknik Gereksinimler:**
- [ ] **Veritabanı Optimizasyonu**
  - [ ] Neo4j indeksleri (`node_type`, `timestamp`)
  - [ ] Qdrant koleksiyon ayarları
- [ ] **WebSocket Optimizasyonu**
  - [ ] Mesaj gruplama (batching) mekanizması
  - [ ] Connection pooling
- [ ] **Frontend Optimizasyonu**
  - [ ] React.memo implementasyonu
  - [ ] useCallback optimizasyonları
  - [ ] Lazy loading bileşenleri

**Başarı Kriteri:** ✅ Kritik API yanıt süreleri <200ms, WebSocket latency <50ms.

---

### **Hafta 2-3: Gelişmiş AI ve Kurumsal Yetenekler**

#### **🤖 Görev 2.1: Gelişmiş AI Entegrasyonu**

**Öncelik:** 🔴 Yüksek  
**Tahmin:** 4 gün  
**Sorumlu:** AI/ML Developer  

**Hedef:** LLM Router'ı akıllandırmak ve Agent öğrenmesini sağlamak.

**Teknik Gereksinimler:**

**2.1.1 Akıllı Model Router**
- [ ] `src/ai/llm_router.py` yeniden tasarım
- [ ] Performans takip sistemi
  ```python
  class PerformanceTracker:
      def track_model_performance(self, model_name, task_type, metrics):
          # Hız, başarı, maliyet metrikleri
          pass
      
      def calculate_fitness_score(self, model_name, task_type):
          # Uygunluk skoru hesaplama
          pass
  ```
- [ ] LLM Response Cache (Redis/Memory)
- [ ] Dinamik model seçim algoritması

**2.1.2 Agent Öğrenme Sistemi**
- [ ] Hata logging sistemi
  ```python
  class LearningSystem:
      def log_failure(self, task_id, output, rejection_reason):
          # Fine-tuning veri seti için kayıt
          pass
      
      def generate_training_data(self):
          # Hata verilerinden öğrenme veri seti
          pass
  ```
- [ ] `GuardianAgent` feedback döngüsü
- [ ] Öğrenme veri seti oluşturma

**Başarı Kriteri:** ✅ Basit görevler için yerel model, karmaşık görevler için bulut modeli otomatik seçimi.

---

#### **🔐 Görev 2.2: Kurumsal Güvenlik Sistemi**

**Öncelik:** 🔴 Yüksek  
**Tahmin:** 5 gün  
**Sorumlu:** Backend + Security Developer  

**Hedef:** Çok kullanıcılı, güvenli ve proje-bazlı erişim kontrolü.

**Teknik Gereksinimler:**

**2.2.1 Kullanıcı Yönetimi**
- [ ] Kullanıcı modeli tasarımı
  ```python
  class User:
      id: str
      username: str
      password_hash: str
      role: UserRole  # admin, developer, viewer
      projects: List[str]
      created_at: datetime
  ```
- [ ] JWT tabanlı kimlik doğrulama
- [ ] FastAPI middleware entegrasyonu
- [ ] Şifre hashleme ve doğrulama

**2.2.2 Rol Tabanlı Erişim Kontrolü (RBAC)**
- [ ] Rol sistemini tanımla
  ```python
  class UserRole(Enum):
      ADMIN = "admin"          # Tüm yetkiler
      DEVELOPER = "developer"  # Proje içi tam yetki
      VIEWER = "viewer"        # Sadece okuma
  ```
- [ ] Endpoint yetkilendirme decorator'ları
- [ ] Permission middleware

**2.2.3 Çoklu Proje Desteği**
- [ ] Tüm veri modellerine `project_id` ekle
  - [ ] Neo4j node schema güncelleme
  - [ ] Qdrant collection separation
  - [ ] PostgreSQL tablo güncellemeleri
- [ ] Proje-bazlı veri filtreleme
- [ ] Proje oluşturma/silme API'leri

**Başarı Kriteri:** ✅ İki kullanıcı kendi projelerini oluşturdukunda, birbirinin verilerini göremiyor.

---

#### **🔌 Görev 2.3: Plugin Mimarisi**

**Öncelik:** 🟡 Orta  
**Tahmin:** 3 gün  
**Sorumlu:** Architecture Developer  

**Hedef:** Genişletilebilir plugin sistemi oluşturmak.

**Teknik Gereksinimler:**
- [ ] `src/plugins/` klasör yapısı
- [ ] `BasePlugin` arayüz tanımı
  ```python
  class BasePlugin(ABC):
      @abstractmethod
      def name(self) -> str: pass
      
      @abstractmethod
      def execute(self, context: PluginContext) -> PluginResult: pass
      
      @abstractmethod
      def validate_input(self, input_data: dict) -> bool: pass
  ```
- [ ] Plugin discovery mekanizması
- [ ] Orchestrator entegrasyonu
- [ ] Plugin dependency yönetimi

**Başarı Kriteri:** ✅ `plugins/` klasörüne eklenen yeni plugin, restart sonrası otomatik tanınıyor.

---

## 📊 Sprint Başarı Kriterleri

### **Teknik Kriterler**
- [ ] **Eş Zamanlılık:** 10+ kullanıcı desteği
- [ ] **Performans:** <200ms API yanıt süresi
- [ ] **Güvenilirlik:** %99.9 uptime
- [ ] **Ölçeklenebilirlik:** 1000+ WebSocket bağlantısı
- [ ] **Veri Kapasitesi:** 10,000+ graph node, 100+ eş zamanlı LLM isteği

### **İşlevsel Kriterler**
- [ ] **Çoklu Proje:** Tam fonksiyonel workspace desteği
- [ ] **Güvenlik:** RBAC ve proje isolation
- [ ] **AI Yetenekleri:** Akıllı model seçimi
- [ ] **Genişletilebilirlik:** Plugin sistemi

### **Kullanıcı Deneyimi**
- [ ] **Arayüz:** Responsive ve real-time updates
- [ ] **API:** RESTful ve WebSocket integration
- [ ] **Dokümantasyon:** Kapsamlı API ve kullanıcı rehberi

---

## 🎯 Görev Takip Tablosu

| Görev | Durumu | Başlangıç | Bitiş | Sorumlu | Notlar |
|-------|--------|-----------|-------|---------|--------|
| 1.1 Neo4j & Qdrant Entegrasyonu | 🔄 | - | - | Backend | |
| 1.2 E2E Test Sistemi | ⏳ | - | - | Full-Stack | |
| 1.3 Performans Optimizasyonu | ⏳ | - | - | Backend | |
| 2.1 Gelişmiş AI Entegrasyonu | ⏳ | - | - | AI/ML | |
| 2.2 Kurumsal Güvenlik | ⏳ | - | - | Backend/Security | |
| 2.3 Plugin Mimarisi | ⏳ | - | - | Architecture | |

**Durum Göstergeleri:**
- 🔄 Devam Ediyor
- ⏳ Beklemede
- ✅ Tamamlandı
- ❌ Engellendi
- 🔴 Risk

---

## 🚨 Risk ve Bağımlılıklar

### **Yüksek Risk Alanları**
1. **Veritabanı Performansı** - Neo4j/Qdrant large scale performance
2. **WebSocket Kararlılığı** - 1000+ concurrent connections
3. **AI Model Costs** - LLM API usage optimization

### **Kritik Bağımlılıklar**
1. Docker infrastrüktürü
2. LLM API erişimi (OpenAI, Anthropic)
3. Frontend-Backend WebSocket protokolü

### **Risk Azaltma Stratejileri**
- [ ] Performans testleri her görev sonrası
- [ ] Rollback planları hazırla
- [ ] Alternative LLM providers
- [ ] Monitoring ve alerting sistemi

---

## 📝 Çıkarılacak Dersler (Retrospektif)

### **Sprint Sonunda Değerlendirilecekler**
- [ ] Hangi teknolojiler beklenenden zor çıktı?
- [ ] Tahminleme doğruluğu nasıldı?
- [ ] Ekip içi kommunikasyon etkinliği
- [ ] Kullanıcı feedback'i ve öncelik değişiklikleri

---

## 📚 Kaynaklar ve Referanslar

- [Neo4j Python Driver Documentation](https://neo4j.com/docs/python-manual/current/)
- [Qdrant Client Library](https://github.com/qdrant/qdrant-client)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright E2E Testing](https://playwright.dev/)

---

**Son Güncelleme:** 2025-01-22  
**Versiyon:** 1.0  
**Hazırlayan:** Sprint Planning Team
