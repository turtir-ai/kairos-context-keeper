# API Dokümantasyonu

## Genel Bilgiler
Kairos API, RESTful prensiplere uygun olarak tasarlanmıştır ve JSON formatında veri alışverişi yapar.

**Base URL**: `http://localhost:8000`

**Content-Type**: `application/json`

## Temel Endpointler

### GET /status
Sistem durumunu sorgular.

**Yanıt Örneği:**
```json
{
  "status": "running",
  "context_engine": "active",
  "agents": ["ResearchAgent", "ExecutionAgent", "GuardianAgent"],
  "memory_systems": ["neo4j", "qdrant"],
  "uptime": "2h 30m"
}
```

### POST /tasks
Yeni görev oluşturur.

**İstek Örneği:**
```json
{
  "title": "Research Sprint 6",
  "description": "Complete Sprint 6 tasks",
  "priority": "high",
  "agent_type": "ResearchAgent"
}
```

**Yanıt Örneği:**
```json
{
  "task_id": "task_001",
  "status": "created",
  "created_at": "2024-12-23T14:30:00Z"
}
```

### GET /tasks/{task_id}
Belirli görevin detaylarını getirir.

**Yanıt Örneği:**
```json
{
  "task_id": "task_001",
  "title": "Research Sprint 6",
  "status": "in_progress",
  "agent": "ResearchAgent",
  "progress": 45,
  "created_at": "2024-12-23T14:30:00Z",
  "updated_at": "2024-12-23T14:35:00Z"
}
```

### GET /memory/summary
Hafıza özetini getirir.

**Yanıt Örneği:**
```json
{
  "neo4j_nodes": 1250,
  "neo4j_relationships": 3400,
  "qdrant_vectors": 5600,
  "total_memory_size": "245MB",
  "last_updated": "2024-12-23T14:30:00Z"
}
```

### POST /memory/search
Hafızada arama yapar.

**İstek Örneği:**
```json
{
  "query": "Sprint 6 backup tasks",
  "limit": 10,
  "threshold": 0.8
}
```

### GET /agents
Mevcut ajanları listeler.

**Yanıt Örneği:**
```json
{
  "agents": [
    {
      "name": "ResearchAgent",
      "status": "active",
      "current_task": "task_001",
      "capabilities": ["web_search", "wikipedia", "github"]
    },
    {
      "name": "ExecutionAgent",
      "status": "idle",
      "capabilities": ["file_operations", "terminal_commands"]
    }
  ]
}
```

### WebSocket Endpoints

#### /ws/tasks
Görev güncellemelerini gerçek zamanlı olarak alır.

**Mesaj Formatı:**
```json
{
  "type": "task_update",
  "task_id": "task_001",
  "status": "completed",
  "progress": 100,
  "timestamp": "2024-12-23T14:45:00Z"
}
```

#### /ws/mcp_context
MCP context güncellemelerini alır.

**Mesaj Formatı:**
```json
{
  "type": "mcp_context_update",
  "task_id": "task_001",
  "context": {
    "system_prompt": "You are a research assistant...",
    "rag_results": [...],
    "tool_definitions": [...]
  },
  "timestamp": "2024-12-23T14:45:00Z"
}
```

## Hata Kodları

- **400 Bad Request**: Geçersiz istek formatı
- **404 Not Found**: Kaynak bulunamadı
- **500 Internal Server Error**: Sunucu hatası

## Otomatik Dokümantasyon

Detaylı API dokümantasyonu için FastAPI'nin otomatik oluşturduğu dokümantasyon sayfasını ziyaret edin:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
