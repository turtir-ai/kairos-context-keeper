# Geliştirici Rehberi

## Proje Mimarisi
Kairos, aşağıdaki ana modüllerden oluşur:

- **Agent System**: Görevleri yürüten autonomous ajanlar
- **Memory System**: Neo4j ve Qdrant ile bilgi yönetimi
- **MCP Integration**: Model Context Protocol entegrasyonu
- **WebSocket Management**: Gerçek zamanlı iletişim
- **Frontend**: React tabanlı kullanıcı arayüzü

## Yeni Agent Ekleme
Yeni bir agent eklemek için:

1. `src/agents/` klasöründe yeni agent sınıfını oluşturun
2. `BaseAgent`'tan miras alın
3. Gerekli metodları implement edin
4. `AgentCoordinator`'a kaydedin

## Test Çalıştırma
```bash
pytest tests/
```

## Katkıda Bulunma
CONTRIBUTING.md dosyasındaki kuralları takip edin.

## Modül Açıklamaları

### BaseAgent
Tüm ajanların türediği temel sınıf

### AgentCoordinator  
Ajanlar arası koordinasyonu sağlayan merkezi yönetici

### MemoryManager
Neo4j ve Qdrant entegrasyonunu yöneten hafıza yöneticisi

### MCP Server
Model Context Protocol sunucusu
