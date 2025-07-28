# 🚀 Sprint 0: Temel Düzeltmeler ve Refactoring - Detaylı Task Takibi

## 📋 Genel Hedef
Mevcut prototipin temel mimari hatalarını gidermek, kod tabanını sağlam, ölçeklenebilir ve yönetilebilir bir hale getirmek.

**Süre:** 1 Hafta  
**Başlangıç Tarihi:** 22 Ocak 2025  
**Bitiş Tarihi:** 29 Ocak 2025

---

## 🎯 Task 1: Controller CLI'ı Güvenilir ve Arka Planda Çalışır Hale Getirmek

### 📝 Açıklama
`kairos start` komutunun daemon'u arka planda gerçekten başlatmasını ve `kairos stop` komutunun güvenilir şekilde durdurabilmesini sağlamak.

### ❌ Mevcut Sorun
- `subprocess.run` komutu ana süreci bloke eder
- Daemon arka planda çalışmaz
- `stop_daemon` fonksiyonu etkisiz

### ✅ Teknik Adımlar

#### 1.1. CLI Start Fonksiyonunu Düzelt
- [ ] `src/cli.py` dosyasını aç
- [ ] `start_daemon` fonksiyonunda `subprocess.run` → `subprocess.Popen` değişikliği yap
- [ ] Process ID'yi `.kairos.pid` dosyasına kaydet
- [ ] Daemon başlatıldığında kullanıcıya bilgi ver ve terminali geri döndür

**Kod Örneği:**
```python
def start_daemon():
    print("🚀 Kairos daemon başlatılıyor...")
    try:
        process = subprocess.Popen(
            [sys.executable, "src/main.py"], 
            cwd=".",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # PID'yi kaydet
        with open(".kairos.pid", "w") as f:
            f.write(str(process.pid))
            
        print(f"✅ Daemon başlatıldı (PID: {process.pid})")
        print("📍 Port: 8000")
        print("🌐 Dashboard: http://localhost:8000/dashboard")
        
    except Exception as e:
        print(f"❌ Hata: {e}")
```

#### 1.2. Stop Fonksiyonunu Yeniden Yaz
- [ ] `.kairos.pid` dosyasını oku
- [ ] Windows için `taskkill`, Linux/macOS için `os.kill` kullan
- [ ] Süreç sonlandırıldıktan sonra PID dosyasını sil

**Kod Örneği:**
```python
def stop_daemon():
    print("🛑 Kairos daemon durduruluyor...")
    try:
        if not os.path.exists(".kairos.pid"):
            print("ℹ️ Çalışan daemon bulunamadı")
            return
            
        with open(".kairos.pid", "r") as f:
            pid = int(f.read().strip())
            
        import platform
        if platform.system() == "Windows":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], check=True)
        else:
            os.kill(pid, signal.SIGTERM)
            
        os.remove(".kairos.pid")
        print("✅ Daemon durduruldu")
        
    except Exception as e:
        print(f"❌ Durdurma hatası: {e}")
```

#### 1.3. Status Fonksiyonunu Güncelle
- [ ] PID dosyası varlığını kontrol et
- [ ] Sürecin çalışıp çalışmadığını doğrula
- [ ] API'ye bağlanmadan önce süreç kontrolü yap

### 🎯 Başarı Kriteri
- [x] `kairos start` anında tamamlanır ve terminal geri döner
- [x] `kairos status` doğru durumu gösterir
- [x] `kairos stop` arka plandaki FastAPI sunucusunu kapatır
- [x] Multiple start/stop cycles sorunsuz çalışır

### 📁 İlgili Dosyalar
- `src/cli.py`

### ⏱️ Tahmini Süre: 2 saat

---

## 🔄 Task 2: Asenkron Altyapıyı Tamamen Asenkron Hale Getirmek

### 📝 Açıklama
FastAPI sunucusunun uzun süren LLM istekleri sırasında bloke olmasını engellemek ve performansı artırmak.

### ❌ Mevcut Sorun
- `_generate_ollama` fonksiyonu içinde senkron `requests.post` kullanıyor
- Bu, sunucuyu bloke eder ve diğer isteklere cevap veremez

### ✅ Teknik Adımlar

#### 2.1. Bağımlılık Ekle
- [ ] `requirements.txt`'e `httpx` kütüphanesini ekle
- [ ] Gerekirse projeyi yeniden yükle

#### 2.2. LLM Router'ı Güncelle
- [ ] `src/llm_router.py` dosyasını aç
- [ ] `requests` import'unu `httpx` ile değiştir
- [ ] `_generate_ollama` fonksiyonunu async hale getir

**Kod Örneği:**
```python
async def _generate_ollama(self, prompt: str, model: str) -> Dict[str, Any]:
    """Generate response using Ollama"""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{self.ollama_base_url}/api/generate",
            json=payload,
            timeout=30
        )
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Ollama API error: {response.status_code}")
```

#### 2.3. CLI Status Güncellemesi (İsteğe Bağlı)
- [ ] `check_status` fonksiyonunda da `httpx` kullan

### 🎯 Başarı Kriteri
- [x] Aynı anda birden fazla `/ai/generate` isteği atılabilir
- [x] Sistem kilitlenmeden tüm isteklere paralel cevap verir
- [x] Response times improved

### 📁 İlgili Dosyalar
- `src/llm_router.py`
- `requirements.txt`
- `src/cli.py` (isteğe bağlı)

### ⏱️ Tahmini Süre: 1.5 saat

---

## 🎭 Task 3: Agent Etkileşimlerini Merkezileştirmek

### 📝 Açıklama
Tüm agent görevlerinin tek bir noktadan (Orchestrator) yönetilmesini sağlayarak sistemi modüler ve izlenebilir hale getirmek.

### ❌ Mevcut Sorun
- `main.py`'deki API endpoint'leri agent'ları doğrudan import ediyor
- `agent_coordinator`'ın varlık amacı ortadan kalkıyor
- Görev sıraya alma, önceliklendirme, izleme devre dışı

### ✅ Teknik Adımlar

#### 3.1. Agent Import'larını Kaldır
- [ ] `src/main.py` dosyasını aç
- [ ] `/agents/...` endpoint'lerindeki tüm `from agents... import ...` satırlarını sil

#### 3.2. Endpoint'leri Task-Based Hale Getir
- [ ] Her endpoint'i `agent_coordinator.create_task()` çağrısı yapacak şekilde değiştir

**Örnek Değişiklik:**
```python
# ESKİ HAL
@app.post("/agents/research")
async def research_topic(request: dict):
    from agents.research_agent import ResearchAgent
    topic = request.get("topic", "")
    if not topic:
        return {"error": "Topic is required"}
    agent = ResearchAgent()
    result = await agent.research(topic)
    return result

# YENİ HAL  
@app.post("/agents/research")
async def research_topic(request: dict):
    from orchestration.agent_coordinator import agent_coordinator, TaskPriority
    
    topic = request.get("topic", "")
    if not topic:
        return {"error": "Topic is required"}
    
    task_id = agent_coordinator.create_task(
        name=f"Research: {topic}",
        agent_type="ResearchAgent",
        parameters={"topic": topic},
        priority=TaskPriority.MEDIUM
    )
    
    return {
        "message": "Research task created successfully", 
        "task_id": task_id,
        "status": "queued"
    }
```

#### 3.3. Task Status Endpoint'ini Zenginleştir
- [ ] `/orchestration/task/{task_id}` endpoint'inin görev durumu ve sonucunu döndürdüğünden emin ol

#### 3.4. Güncellenecek Endpoint'ler
- [ ] `/agents/execute` → Task-based
- [ ] `/agents/validate` → Task-based  
- [ ] `/agents/research` → Task-based
- [ ] `/ai/retrieve` → Task-based

### 🎯 Başarı Kriteri
- [x] Agent endpoint'leri anında `task_id` ile yanıt döner
- [x] `agent_coordinator`'ın kuyruğunda yeni görevler belirir
- [x] Görev sonuçları `/orchestration/task/{task_id}` ile alınabilir
- [x] No direct agent imports in main.py

### 📁 İlgili Dosyalar
- `src/main.py`

### ⏱️ Tahmini Süre: 3 saat

---

## 🧠 Task 4: Hafıza Katmanını Birleştirmek ve Gerçekçi Hale Getirmek

### 📝 Açıklama
Projenin hafıza operasyonlarını tek bir, tutarlı ve genişletilebilir sınıf üzerinden yönetmek.

### ❌ Mevcut Sorun
- Birden fazla kopuk hafıza dosyası var
- "Enhanced" aslında sadece Python sözlüğü, gerçek DB değil
- Inconsistent interfaces

### ✅ Teknik Adımlar

#### 4.1. Yeni Memory Manager Oluştur
- [ ] `src/memory/memory_manager.py` dosyasını oluştur
- [ ] `MemoryManager` sınıfını tanımla

#### 4.2. Database Bağlantı Mantığı
- [ ] `__init__` metodunda Neo4j ve Qdrant'a bağlanmayı dene
- [ ] Ortam değişkenlerinden bağlantı bilgilerini oku (`.env` dosyası)
- [ ] Bağlantı başarısız olursa fallback mechanism kur

**Kod Iskelet:**
```python
class MemoryManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Connection attempts
        self.neo4j_available = False
        self.qdrant_available = False
        
        # Fallback storage
        self.local_storage = {
            "nodes": {},
            "edges": {},
            "vectors": {},
            "metadata": {}
        }
        
        self._initialize_connections()
        
    def _initialize_connections(self):
        # Try Neo4j connection
        try:
            # Neo4j connection code
            self.neo4j_available = True
        except:
            self.logger.warning("Neo4j not available, using local storage")
            
        # Try Qdrant connection  
        try:
            # Qdrant connection code
            self.qdrant_available = True
        except:
            self.logger.warning("Qdrant not available, using local storage")
```

#### 4.3. Unified Interface
- [ ] Tüm hafıza fonksiyonlarını tek sınıf altında birleştir:
  - `add_node()`
  - `add_edge()` 
  - `query_nodes()`
  - `add_context_memory()`
  - `query_context()`
  - `get_stats()`

#### 4.4. Main.py Güncellemesi
- [ ] Hafıza endpoint'lerini yeni `MemoryManager` kullanacak şekilde güncelle

#### 4.5. Eski Dosyaları Temizle
- [ ] Artık kullanılmayan hafıza dosyalarını sil:
  - `enhanced_knowledge_graph.py` → Silinecek
  - `neo4j_integration.py` → Entegre edilecek
  - Diğer gereksiz hafıza dosyaları

### 🎯 Başarı Kriteri
- [x] Tüm hafıza API'ları yeni `MemoryManager` üzerinden çalışır
- [x] Docker servisleri çalışmıyorken sistem çökmez
- [x] Yerel dosya tabanlı fallback çalışır
- [x] Consistent interface across all memory operations

### 📁 İlgili Dosyalar
- Yeni: `src/memory/memory_manager.py`
- Güncellenecek: `src/main.py`, `docker-compose.yml`
- Silinecek: Eski hafıza dosyaları

### ⏱️ Tahmini Süre: 4 saat

---

## 📊 Sprint 0 Özet

### ⏰ Toplam Tahmini Süre: 10.5 saat (1.5 gün)

### 🎯 Sprint Sonrası Beklenen Sonuçlar
1. **Güvenilir CLI:** Daemon gerçekten arka planda çalışır
2. **Performant API:** Async altyapı ile bloke olmayan sunucu
3. **Merkezi Orchestration:** Tüm agent çağrıları koordinatör üzerinden
4. **Unified Memory:** Tek, tutarlı hafıza yönetim sistemi

### ✅ Başarı Kriterleri Genel Kontrolü
- [ ] Terminal `kairos start` ile anında geri döner
- [ ] Aynı anda birden fazla API isteği işlenebilir  
- [ ] Agent endpoint'leri task_id döner
- [ ] Hafıza API'ları sorunsuz çalışır
- [ ] Sistem Docker olmadan da çalışır

### 📝 Test Senaryoları
1. **CLI Test:** Start → Status → Stop → Status cycle
2. **Async Test:** Concurrent `/ai/generate` requests
3. **Orchestration Test:** Create task → Check status → Get result
4. **Memory Test:** Add node → Query → Add context → Query

---

## 🚀 Sonraki Adım
Sprint 0 tamamlandıktan sonra **Sprint 1: Flow Engineering ve Agent Orkestrasyonu** başlatılacak.

**Task Takip:** Her task tamamlandığında ✅ ile işaretlenecek ve test sonuçları not edilecek.
