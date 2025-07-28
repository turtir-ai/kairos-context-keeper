# Sprint 6: Tam Otonomi, Kalıcı Hafıza ve Kurumsal Hazırlık (Detaylı Plan)

**Sprint Hedefi:** Kairos'un tüm bileşenlerini uçtan uca entegre ederek, bir görevin oluşturulmasından tamamlanmasına kadar olan tüm yaşam döngüsünü **tam otonom** bir şekilde yönetmesini sağlamak. Agent'ların ürettiği sonuçların **kalıcı hafızaya** kaydedilmesi, sistemin **kendi performansından öğrenmesi** ve **kurumsal düzeyde güvenlik ve test altyapısına** sahip olması bu sprintin ana hedefleridir.

---

### **Faz 1: Kalıcı Hafıza ve Agent Yeteneklerinin Tamamlanması (1 Hafta)**

#### **Görev 1.1: MCP ve Hafıza Yöneticisi (MemoryManager) Arasındaki Köprüyü Kurma**

* **Hedef:** MCP üzerinden oluşturulan bağlamın, projenin uzun dönemli hafızasına (Neo4j & Qdrant) kalıcı olarak kaydedilmesini sağlamak.
* **Teknik Adımlar:**
  1. `src/mcp/mcp_server.py` içinde, `MemoryManager`'dan bir nesne örneği al.
  2. `MCP` sınıfına `persist_context` adında yeni bir asenkron metod ekle. Bu metod, bir görev tamamlandığında veya önemli bir bağlam oluştuğunda çağrılmalıdır.
  3. `persist_context` metodu, MCP'nin o anki `context_data`'sını almalı ve bunu standart "Kairos Atomu" formatına dönüştürmelidir.
  4. Bu "atomu", `memory_manager.add_node` ve `memory_manager.add_context_memory` metodlarını çağırarak hem Bilgi Grafı'na (Neo4j) hem de Vektör Veritabanı'na (Qdrant) işlemelidir. İlişkisel bağlamlar için (`based_on`, `corrects` gibi) `add_edge` kullanılmalıdır.

#### **Görev 1.2: Tüm Agent'ları MCP Uyumlu Hale Getirme ve Gerçek Yetenekler Ekleme**

* **Hedef:** Tüm agent'ların (`ResearchAgent`, `GuardianAgent` vb.) görevlerini yürütürken MCP'den bağlam almasını ve sonuçlarını MCP üzerinden raporlamasını sağlamak.
* **Teknik Adımlar:**
  1. `BaseAgent` sınıfını, `mcp_context` adında bir parametre alacak şekilde güncelle.
  2. `AgentCoordinator`'daki görev yürütme mantığını, görevi başlatmadan önce ilgili bağlamı `MemoryManager`'dan çekip bir MCP nesnesi oluşturacak ve bunu agent'a parametre olarak geçecek şekilde refactor et.
  3. **`ResearchAgent`'ı Geliştir:** Daha önce eklenen `research_tools.py`'yi kullanarak, `research` metodunun gerçekten web scraping (BeautifulSoup), Wikipedia API ve GitHub API çağrıları yapmasını sağla.
  4. **`ExecutionAgent`'ı Güçlendir:** Agent'ın, sadece basit terminal komutları değil, aynı zamanda dosya sistemi işlemleri (dosya oluşturma, yazma, silme) yapabilmesini sağlayan metodlar ekle.
  5. **`GuardianAgent`'ı Entegre Et:** `ExecutionAgent` bir kod ürettiğinde, `AgentCoordinator`'ın otomatik olarak bir "validation" görevi oluşturup `GuardianAgent`'ı tetiklemesini sağla.

---

### **Faz 2: Arayüzün Tamamlanması ve Uçtan Uca Testler (1 Hafta)**

#### **Görev 2.1: Frontend'de MCP Bağlamını Görselleştirme**

* **Hedef:** Kullanıcının, bir görev yürütülürken LLM'in hangi bağlamı "gördüğünü" arayüz üzerinden anlık olarak izleyebilmesini sağlamak.
* **Teknik Adımlar:**
  1. **Yeni WebSocket Event'i:** `WebSocketManager`'a `mcp_context_update` adında yeni bir event türü ekle. `AgentCoordinator`, bir göreve bağlam enjekte ettiğinde bu event'i yayınlamalı.
  2. **Yeni React Bileşeni:** `TaskOrchestrator` sayfasına, seçili bir görevin detaylarını gösteren bir "Task Detail" paneli ekle.
  3. Bu panel, `mcp_context_update` event'ini dinlemeli ve gelen bağlam verisini (sistem prompt'u, RAG sonuçları, araç tanımları vb.) formatlanmış bir şekilde (örn: JSON viewer veya sekmeli bir arayüz) göstermeli.

#### **Görev 2.2: Kapsamlı Test Suite'i Oluşturma ve Performans Benchmark'ı**

* **Hedef:** Sistemin güvenilirliğini ve performansını objektif metriklerle ölçmek.
* **Teknik Adımlar:**
  1. **Entegrasyon Testleri:** `tests/` klasörüne `test_full_workflow.py` ekle. Bu test, bir PRD'den görev oluşturulmasından, agent'ların çalışmasına, sonucun hafızaya kaydedilmesine ve arayüzde güncellenmesine kadar olan tüm süreci uçtan uca test etmeli.
  2. **Yük Testi (Load Testing):** `locust` veya benzeri bir araç kullanarak, WebSocket sunucusuna aynı anda 1000+ bağlantı simüle et ve API endpoint'lerine saniyede 100+ istek göndererek sistemin yük altındaki davranışını ölç.
  3. **Benchmark Script'i:** `scripts/benchmark.py` adında bir script oluştur. Bu script, standart bir dizi görevi (kod yazma, araştırma, analiz) 100 kez çalıştırarak ortalama görev tamamlama süresini, LLM maliyetini ve başarı oranını ölçmeli ve bir rapor oluşturmalı.

---

### **Faz 3: Kurumsal Hazırlık ve Dokümantasyon (1 Hafta)**

#### **Görev 3.1: Kullanıcı ve Geliştirici Dokümantasyonunu Tamamlama**

* **Hedef:** Projenin nasıl kullanılacağını, kurulacağını ve geliştirileceğini anlatan kapsamlı dokümanlar hazırlamak.
* **Teknik Adımlar:**
  1. **Kullanıcı Rehberi:** `docs/user_guide.md` oluştur. İçeriği:
     * Kairos nasıl kurulur? (`docker-compose` ve manuel kurulum).
     * İlk proje nasıl başlatılır (`kairos init`).
     * Dashboard nasıl kullanılır? (Her sayfanın ekran görüntüsü ve açıklaması).
     * Görev nasıl oluşturulur ve takip edilir?
  2. **API Dokümantasyonu:** FastAPI'nin otomatik oluşturduğu `/docs` sayfasını zenginleştir. Her endpoint için detaylı açıklamalar, örnek istek ve yanıt formatları ekle.
  3. **Geliştirici Rehberi:** `docs/developer_guide.md` oluştur. İçeriği:
     * Proje mimarisi ve modüllerin açıklaması.
     * Yeni bir agent nasıl eklenir?
     * Testler nasıl çalıştırılır?
     * Katkıda bulunma kuralları (`CONTRIBUTING.md`).

#### **Görev 3.2: Veri Yedekleme ve Kurtarma Mekanizması**

* **Hedef:** Kritik proje verilerinin (hafıza) kaybolmasını önlemek için bir yedekleme ve kurtarma stratejisi oluşturmak.
* **Teknik Adımlar:**
  1. `scripts/backup.py` script'i oluştur. Bu script, Neo4j ve Qdrant veritabanlarından periyodik olarak (örn: her gece) snapshot almalı ve bunları sıkıştırılmış bir formatta (`.tar.gz`) disk'e kaydetmeli.
  2. `scripts/restore.py` script'i oluştur. Bu script, alınan bir yedekten veritabanlarını eski haline getirebilmeli.
  3. Bu script'leri çalıştıracak `kairos backup` ve `kairos restore` komutlarını `cli.py`'ye ekle.

Bu sprint planı, Kairos'u teknik olarak tamamlanmış, test edilmiş, güvenli, iyi dokümante edilmiş ve **üretime bir adım kalmış** bir ürün haline getirecektir.
