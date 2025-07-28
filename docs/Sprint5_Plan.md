# **Sprint 5: Otonom Öğrenme, Kurumsal Yetenekler ve Üretim Optimizasyonu (Detaylı Plan)**

**Sprint Hedefi:** Kairos'u, metrik tabanlı kararlar alabilen, kendi modellerini eğitebilen, çok kullanıcılı proje ortamlarını destekleyen ve üretime hazır, ölçeklenebilir bir platforma dönüştürmek.

---

### **Faz 1: Otonom Öğrenme ve Akıllı Zeka Katmanının İnşası (1 Hafta)**

**Amaç:** Kairos'un "kendi kendine gelişen" ruhunu hayata geçirmek.

#### **Görev 1.1: Metrik Odaklı, Akıllı LLM Router Geliştirme**

*   **Hedef:** `LLMRouter`'ın, basit anahtar kelime kontrolleri yerine, gerçek performansa dayalı olarak en uygun LLM'i seçmesini sağlamak.
*   **Teknik Adımlar:**
    1.  **Veritabanı Şeması:** `performance_tracker`'ın topladığı metrikleri (hız, başarı oranı, maliyet, token kullanımı) kalıcı olarak saklamak için bir PostgreSQL tablosu (`model_performance_metrics`) oluştur.
    2.  **Puanlama Algoritması:** `LLMRouter` içinde `_calculate_model_score` adında bir metod yaz. Bu metod, bir görev (`task_type`) için, veritabanındaki geçmiş performans metriklerini, modelin yeteneklerini (`specialties`) ve anlık sağlık durumunu (`health_status`) kullanarak her model için bir "uygunluk skoru" hesaplamalıdır.
    3.  **Dinamik Seçim:** `select_model` fonksiyonunu, bu skorlama algoritmasını kullanacak şekilde yeniden yaz. En yüksek skora sahip olan, sağlıklı ve uygun modeli seçmeli.
    4.  **LLM Yanıt Önbelleği (Caching):** Sık yapılan ve deterministik olan isteklerin (örn: "proje özetini ver") sonuçlarını önbelleğe almak için bir Redis entegrasyonu ekle. Bir istek geldiğinde önce Redis'i kontrol et, sonuç yoksa LLM'e git.
*   **İlgili Dosyalar:** `src/llm_router.py`, `src/monitoring/performance_tracker.py`, `docker-compose.yml` (Redis servisi için).
*   **Başarı Kriteri:** "Basit kod yaz" ve "karmaşık analiz yap" görevleri 10'ar kez çalıştırıldığında, `LLMRouter`'ın zamanla ilk görev için daha çok yerel ve hızlı modelleri, ikinci görev için ise daha güçlü modelleri tercih etmeye başladığının log'lardan gözlemlenmesi.

#### **Görev 1.2: Otonom Fine-Tuning Veri Toplama ve Eğitim Pipeline'ı Kurma**

*   **Hedef:** Sistemin, `GuardianAgent` tarafından reddedilen veya kullanıcı tarafından manuel olarak düzeltilen çıktılardan öğrenerek, yerel modelleri otomatik olarak eğitebilmesini sağlamak.
*   **Teknik Adımlar:**
    1.  **Veri Toplama Mekanizması:** `AgentCoordinator`'da, bir görev başarısız olduğunda veya bir `GuardianAgent` denetiminden geçemediğinde, bu olayı (`task_id`, `prompt`, `hatalı_çıktı`, `düzeltme_sebebi`) bir `fine_tuning_dataset` PostgreSQL tablosuna kaydet.
    2.  **Veri Etiketleme Arayüzü (Basit):** Dashboard'a, bu veri setini listeleyen ve kullanıcının "doğru" çıktıyı manuel olarak girmesine veya onaylamasına olanak tanıyan basit bir arayüz ekle.
    3.  **Eğitim Script'i:** `src/fine_tuning/trainer.py` adında bir script oluştur. Bu script:
        *   Veritabanından onaylanmış eğitim verilerini çekmeli.
        *   Hugging Face `transformers` ve `peft` kütüphanelerini kullanarak, seçilen bir yerel model (örn: `Devstral-Small`) üzerinde **QLoRA** ile 4-bit ince ayar yapmalı.
        *   Eğitilmiş yeni LoRA adaptörünü, versiyonlanmış bir şekilde disk'e (`models/lora_adapters/`) kaydetmeli.
    4.  **Yeni Modeli Yükleme:** `LLMRouter`'ı, başlangıçta bu adaptörleri kontrol edecek ve Ollama modellerini bu eğitilmiş katmanlarla yükleyecek şekilde güncelle.
*   **İlgili Dosyalar:** `src/orchestration/agent_coordinator.py`, `src/fine_tuning/trainer.py`, `src/llm_router.py`.
*   **Başarı Kriteri:** Birkaç hatalı görev verisi oluşturulduktan sonra, `kairos fine-tune` komutu çalıştırıldığında, yeni bir LoRA adaptörünün oluşturulması ve bir sonraki benzer görevde, modelin daha doğru bir çıktı ürettiğinin gözlemlenmesi.

---

### **Faz 2: Kurumsal Yetenekler ve Çoklu Proje Desteği (1 Hafta)**

**Amaç:** Kairos'u, tek kullanıcılı bir araçtan, ekiplerin güvenle ve izole bir şekilde kullanabileceği çoklu proje platformuna dönüştürmek.

#### **Görev 2.1: Çoklu Proje ve Çalışma Alanı (Workspace) Mimarisi**

*   **Hedef:** Kullanıcıların birden fazla projeyi, birbirinin verisini görmeden, tamamen izole bir şekilde yönetebilmesini sağlamak.
*   **Teknik Adımlar:**
    1.  **Veritabanı Şeması Güncellemesi:** Tüm veritabanı tablolarına (`PostgreSQL`, `Neo4j` düğümleri, `Qdrant` vektörleri) bir `project_id` alanı ekle.
    2.  **API Yetkilendirme Katmanı:** `api/auth.py`'deki JWT token'larına, kullanıcının o anki aktif `project_id`'sini ekle. Tüm API endpoint'lerine, isteğin sadece o `project_id`'ye ait veriler üzerinde işlem yapmasını zorunlu kılan bir dependency ekle.
    3.  **Kullanıcı Arayüzü:**
        *   Dashboard'a, kullanıcının projeleri arasında geçiş yapmasını sağlayan bir "Proje Seçici" (dropdown menü) ekle.
        *   Yeni bir proje oluşturmak için bir "Create Project" modal'ı tasarla.
    4.  **Daemon İzolasyonu:** `AgentCoordinator`'ın, görevleri ve agent'ları `project_id`'ye göre gruplandırmasını sağla. Bir projede çalışan bir agent'ın, başka bir projenin hafızasına erişemediğinden emin ol.
*   **Başarı Kriteri:** İki farklı kullanıcı (A ve B), kendi projelerini (Proje X ve Proje Y) oluşturduğunda, A kullanıcısının B'nin görevlerini, hafızasını veya agent durumlarını hiçbir API endpoint'i veya arayüz bileşeni üzerinden göremediğinin testlerle doğrulanması.

#### **Görev 2.2: Gelişmiş Konfigürasyon ve Plugin Mimarisi**

*   **Hedef:** Sistemin yeteneklerinin, çekirdek koda dokunmadan, eklentilerle (plugins) genişletilebilmesini sağlamak.
*   **Teknik Adımlar:**
    1.  **Plugin Altyapısı:**
        *   `src/plugins/` adında bir klasör oluştur.
        *   `BasePlugin` adında bir arayüz (abstract class) tanımla. Bu arayüz, `get_name()`, `get_capabilities()` ve `execute(task)` gibi metodları içermeli.
        *   `AgentCoordinator`'ın başlangıçta bu klasörü tarayarak, `BasePlugin`'den türeyen tüm sınıfları dinamik olarak yükleyip bir "plugin" agent'ı olarak kaydetmesini sağla.
    2.  **Dinamik Konfigürasyon:** Sistemin, `kairos.toml` gibi bir merkezi konfigürasyon dosyasından ayarları (örn: `max_concurrent_tasks`, `default_llm_model`) okumasını sağla. Bu ayarların, sistem çalışırken bir API endpoint'i üzerinden güncellenebilmesini mümkün kıl.
*   **Başarı Kriteri:** `plugins` klasörüne, "hava durumunu getiren" basit bir `WeatherPlugin.py` dosyası eklendiğinde, sistem yeniden başlatıldığında `WeatherAgent`'ın otomatik olarak kullanılabilir hale gelmesi ve bir görev olarak çağrılabilmesi.

---

### **Faz 3: Üretim Optimizasyonu ve Ölçeklenebilirlik (3-5 Gün)**

**Amaç:** Sistemin yüksek trafik altında bile performanslı ve güvenilir çalışmasını sağlamak.

#### **Görev 3.1: Yatay Ölçeklendirme ve Yük Dengeleme**

*   **Hedef:** Kairos Daemon'un birden fazla kopyasının (instance) aynı anda çalışabilmesini sağlamak.
*   **Teknik Adımlar:**
    1.  **Durum (State) Yönetimi:** `AgentCoordinator`'daki görev kuyruğu gibi geçici durumları, paylaşımlı bir Redis sunucusuna taşı. Bu, her daemon instance'ının aynı görev kuyruğunu görmesini sağlar.
    2.  **Kubernetes Dağıtımı:** Proje için `Helm Chart` veya `Kustomize` yapılandırmaları oluştur. Bu yapılandırmalar, daemon, veritabanları ve arayüz için `Deployment`, `Service`, `PersistentVolumeClaim` ve `Ingress` kaynaklarını tanımlamalı.
    3.  **Yük Dengeleyici (Load Balancer):** Gelen API ve WebSocket isteklerini, çalışan daemon kopyaları arasında dağıtan bir yük dengeleyici (örn: Nginx Ingress Controller) kur.
*   **Başarı Kriteri:** Kubernetes üzerinde `replicas: 3` ile 3 adet Kairos Daemon pod'u çalıştırıldığında, bir pod çökse bile sistemin kesintisiz olarak görevleri işlemeye devam etmesi.

#### **Görev 3.2: Gelişmiş Gözlemlenebilirlik (Observability)**

*   **Hedef:** Sistemin iç işleyişini detaylı olarak izleyip, sorunları proaktif olarak tespit etmek.
*   **Teknik Adımlar:**
    1.  **APM Entegrasyonu:** `OpenTelemetry` kütüphanesini kullanarak, tüm API isteklerini ve agent görevlerini "trace" et. Bu trace'leri `Jaeger` veya `Datadog` gibi bir APM sistemine gönder.
    2.  **Metrik Paneli:** `Prometheus` ve `Grafana` için bir `docker-compose` yapılandırması ekle. `performance_tracker`'ın, metrikleri Prometheus formatında sunmasını sağla. Grafana'da, sistem sağlığını, agent performansını ve görev istatistiklerini gösteren hazır bir dashboard oluştur.
    3.  **Uyarı (Alerting) Sistemi:** Grafana veya Prometheus Alertmanager'ı kullanarak, kritik eşikler aşıldığında (örn: "hata oranı %5'in üzerine çıktı", "CPU kullanımı %90'ı geçti") bir bildirim (örn: Slack, e-posta) gönderen kurallar tanımla.
*   **Başarı Kriteri:** Grafana dashboard'unda, sistemin canlı performans metriklerinin (görev tamamlama süresi, LLM yanıt hızı vb.) anlık olarak izlenebilmesi. Bir agent çöktüğünde, otomatik olarak bir uyarı tetiklenmesi.
