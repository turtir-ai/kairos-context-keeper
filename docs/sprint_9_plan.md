# Sprint 9: Derin Zeka Aktivasyonu ve Otonom Optimizasyon (Nihai Geliştirme Planı)

**Sprint Hedefi:** Kairos'u, sadece bilgi toplayan bir sistemden, topladığı bilgileri **analiz ederek derin, eyleme geçirilebilir ve spesifik öneriler** üreten, kendi kod tabanını ve performansını **otonom olarak optimize edebilen** akıllı bir süpervizöre dönüştürmek. Bu sprint, Kairos'un "bilen" bir sistemden, **"anlayan, akıl yürüten ve eyleme geçen"** bir sisteme evrimleştiği aşamadır.

---

## Faz 1: Derin Kod ve Mimari Analizi Motorunun İnşası (1 Hafta)

**Amaç:** Kairos'un, bir projenin sadece dosyalarını değil, kodun içindeki mantığı, ilişkileri, potansiyel hataları ve mimari desenleri anlayabilmesini sağlamak. Bu, MCP'nin "yüzeysel" analiz sorununu kökünden çözecektir.

#### ✅ Görev 1.1: Kod Tabanının Bilgi Grafı'na (Knowledge Graph) Dönüştürülmesi

* **Hedef:** `code-graph-rag` projesinden ilhamla, Kairos'un tüm kod tabanını, ilişkisel olarak sorgulanabilir bir Bilgi Grafı'na dönüştürmesini sağlamak.
* **Teknik Adımlar:**
    1. ✅ **Code Parser Modülü:** `src/core/code_parser.py` adında yeni bir modül oluştur. `Tree-sitter` kütüphanesini kullanarak, projedeki tüm Python, JavaScript ve diğer desteklenen dillerdeki dosyaları parse eden ve bir AST (Abstract Syntax Tree) çıkaran bir `CodeParser` sınıfı geliştir.
    2. ✅ **AST-to-Graph Converter:** `src/memory/ast_converter.py` adında bir modül oluştur. Bu modül, `CodeParser`'dan gelen AST'yi alıp, Neo4j'e yüklenecek Cypher `CREATE` ve `MERGE` sorgularına dönüştürmelidir.
        * ✅ **Düğümler (Nodes):** `Module`, `Class`, `Function`, `Variable` gibi tiplere sahip olmalı. Her düğüm, dosya yolu, başlangıç/bitiş satırı gibi meta verileri içermelidir.
        * ✅ **Kenarlar (Edges/Relationships):** `IMPORTS`, `CALLS`, `INHERITS_FROM`, `HAS_VARIABLE` gibi ilişkileri temsil etmelidir.
    3. 🔄 **Otomatik Graf Güncelleme:** Kairos Daemon'daki dosya izleyiciyi (`FileSystemWatcher`), bir dosya değiştiğinde `CodeParser` ve `ASTConverter`'ı otomatik olarak tetikleyecek şekilde güncelle. Bu, Bilgi Grafı'nın her zaman kod tabanıyla senkronize kalmasını sağlar. `kairos init` komutu, projenin ilk tam grafını oluşturmalıdır.
* **İlgili Dosyalar:** ✅ `src/core/code_parser.py`, ✅ `src/memory/ast_converter.py`, 🔄 `src/daemon.py`.
* **Başarı Kriteri:** Proje dizinindeki bir fonksiyonda değişiklik yapıldığında, bu değişikliğin 10 saniye içinde Neo4j'deki ilgili `Function` düğümüne ve ilişkilerine yansıdığının doğrulanması.

#### ✅ Görev 1.2: MCP Araçlarının Derin Analiz Yetenekleriyle Güçlendirilmesi

* **Hedef:** `kairos.analyzeCode` ve `kairos.getContext` MCP araçlarını, bu yeni Bilgi Grafı'nı kullanarak yüzeysel bilgi yerine derinlemesine analizler sunacak şekilde yeniden yapılandırmak.
* **Teknik Adımlar:**
    1. ✅ **Doğal Dil'den Cypher'a Çeviri:** `src/mcp/kairos_mcp_final.py` içinde, `analyzeCode` aracının, gelen doğal dil sorgularını yorumlayarak **önceden tanımlanmış Cypher sorgularına** yönlendirmesini sağlayan bir mantık ekle.
    2. ✅ **Yeni Analiz Yetenekleri Ekle:** Aşağıdaki analizleri yapabilen, önceden tanımlanmış Cypher sorgu şablonları oluştur:
        * ✅ **Etki Analizi (Impact Analysis):** "Bu fonksiyonu değiştirirsem hangi modüller etkilenir?" -> `MATCH (f:Function {name: '...'})<-[:CALLS*1..5]-(caller) RETURN caller.name`
        * ✅ **Döngüsel Bağımlılık Tespiti (Circular Dependency):** Graf üzerinde `a -> b -> a` gibi döngüleri arayan bir Cypher sorgusu geliştir.
        * ✅ **"Ölü Kod" Tespiti (Dead Code Detection):** Hiçbir yerden `CALLS` ilişkisi almayan `Function` düğümlerini listele.
        * ✅ **Teknik Borç Analizi:** `TODO`, `FIXME` gibi yorumları içeren kod düğümlerini ve ortalama fonksiyon uzunluğu gibi karmaşıklık metriklerini hesaplayarak bir "teknik borç skoru" üret.
* **İlgili Dosyalar:** ✅ `src/mcp/kairos_mcp_final.py`, ✅ `src/memory/ast_converter.py`.
* **Başarı Kriteri:** Cursor IDE'den `#[kairos.analyzeCode("find dead code in src/agents")]` komutu çağrıldığında, sistemin Bilgi Grafı'nı sorgulayarak kullanılmayan fonksiyonların bir listesini başarıyla döndürmesi.

---

### Faz 2: Otonom Optimizasyon ve Kendi Kendini İyileştirme (1 Hafta)

**Amaç:** Kairos'un, tespit ettiği sorunları sadece raporlamakla kalmayıp, kullanıcı onayıyla **otonom olarak çözebilen** ve bu süreçten **öğrenen** bir sisteme dönüşmesi.

#### Görev 2.1: Proaktif ve Eyleme Dönüştürülebilir Öneri Mekanizması

* **Hedef:** `SupervisorAgent`'ın ürettiği önerileri, genel tavsiyelerden, spesifik ve tek tıkla uygulanabilir eylemlere dönüştürmek.
* **Teknik Adımlar:**
    1. `SupervisorAgent`, Faz 1'de tespit ettiği bir sorunu (örn: "döngüsel bağımlılık bulundu"), bir LLM'e göndererek bunu bir "görev tanımına" ve "çözüm planına" dönüştürmeli.
    2. Arayüzdeki "Supervisor Insights" paneline, her önerinin yanında bir **eylem türü** (`Refactor`, `Create Task`, `Fix Code`) ve bir **"Uygula"** butonu ekle. Ayrıca, önerinin arkasındaki **kanıtları** (ilgili KG düğümleri, log satırları) gösteren bir "Detayları Gör" bölümü ekle.
* **Başarı Kriteri:** Arayüzde "A ve B modülleri arasında döngüsel bağımlılık tespit edildi" uyarısının yanında, "Refactor Et" butonunun belirlemesi.

#### Görev 2.2: AST Tabanlı Güvenli Kod Refactoring ve Otomatik Test

* **Hedef:** "Ölü kodu sil" veya "fonksiyon adını değiştir" gibi refactoring işlemlerinin, projenin geri kalanını bozmadan, güvenli bir şekilde yapılmasını sağlamak.
* **Teknik Adımlar:**
    1. `ExecutionAgent`'a, `code-graph-rag`'deki "surgical patching" (cerrahi yama) konseptini entegre et. Agent, metin tabanlı arama-değiştirme yapmak yerine, kodun **AST'sini manipüle ederek** değişikliği yapmalı ve ardından kodu yeniden oluşturmalıdır.
    2. **Otomatik Test Tetikleme:** Bir refactoring işlemi tamamlandığında, `AgentCoordinator`'ın, Bilgi Grafı'nı kullanarak etkilenen modüllerle ilgili **birim testlerini otomatik olarak çalıştırmasını** sağla.
    3. Eğer testler başarısız olursa, yapılan değişikliği **otomatik olarak geri almalı** (`git revert`) ve kullanıcıya bir bildirim göndermelidir.
* **Başarı Kriteri:** Kullanıcı "`utils.py`'deki `helper_function` adını `utility_function` olarak değiştir" eylemini onayladığında, agent'ın bu değişikliği ve bu fonksiyonu çağıran diğer tüm dosyalardaki çağrıları AST üzerinden güvenli bir şekilde güncellemesi ve ardından ilgili testleri başarıyla çalıştırması.

---

### Faz 3: AI Chat'in Tam Entegrasyonu ve Kullanıcı Deneyimini Mükemmelleştirme (1 Hafta)

**Amaç:** AI Chat'i, projenin tüm bu yeni derin zeka yeteneklerine erişebilen ana arayüz haline getirmek.

#### Görev 3.1: AI Chat'in Derin Hafıza Pipeline'ına Bağlanması

* **Hedef:** AI Chat'in her isteğini, Faz 1'de inşa edilen akıllı geri çağırma (retrieval) pipeline'ından geçirmek.
* **Teknik Adımlar:**
    1. `src/main.py` içindeki `/ai/generate` endpoint'ini, şu akışı takip edecek şekilde tamamen yeniden yaz:
        a. Gelen `prompt`'u `IntentParser`'a gönder.
        b. Çıkan niyeti `RetrievalAgent`'a göndererek hem KG'den hem de Vektör DB'den hibrit arama yap.
        c. Dönen ham bilgileri `ContextSynthesizer`'a göndererek nihai "süper-prompt"u oluştur.
        d. Bu "süper-prompt"u `LLMRouter`'a göndererek nihai cevabı al.
* **Başarı Kriteri:** AI Chat'e "Projemdeki en karmaşık fonksiyon hangisi?" diye sorulduğunda, sistemin arka planda Bilgi Grafı'nı sorgulayarak doğru cevabı vermesi.

#### Görev 3.2: Kaynak Gösterimli ve "Düşünen" Arayüz

* **Hedef:** Kullanıcının, AI'ın cevabının nereden geldiğini görmesini ve AI'ın düşünme sürecini izleyebilmesini sağlamak.
* **Teknik Adımlar:**
    1. **Kaynak Gösterimi (Citation):** AI Chat'in döndürdüğü her cevabın yanında, bilginin kaynağı olan dosya adına, KG düğümüne veya web linkine tıklanabilir referanslar ekle.
    2. **"Düşünme" Animatörü:** AI Chat'in basit "yazıyor..." animatörünü, backend'den gelen WebSocket güncellemeleriyle ("Niyet anlaşılıyor...", "Bilgi Grafı taranıyor...", "Sonuçlar sentezleniyor...") anlık olarak güncellenen daha gelişmiş bir durum göstergesiyle değiştir.
* **Başarı Kriteri:** Kullanıcı bir soru sorduğunda, cevap gelmeden önce arayüzde AI'ın o an ne yaptığını gösteren en az 3 farklı durum mesajının belirmesi. Cevap geldiğinde ise, en az bir cümlenin yanında tıklanabilir bir kaynak linkinin olması.
