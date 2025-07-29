"""
Merkezi konfigürasyon sistemi.
Tüm yapılandırmayı tek bir yerde toplar ve döngüsel bağımlılıkları önler.
"""
import os
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path

# Loglama yapılandırması
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Veritabanı konfigürasyonu"""
    database_url: str
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    qdrant_host: str
    qdrant_port: int
    qdrant_collection: str

@dataclass
class LLMConfig:
    """LLM konfigürasyonu"""
    openai_api_key: Optional[str]
    anthropic_api_key: Optional[str]
    default_model: str
    temperature: float
    max_tokens: int

@dataclass
class SecurityConfig:
    """Güvenlik konfigürasyonu"""
    secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int

@dataclass
class ServerConfig:
    """Sunucu konfigürasyonu"""
    host: str
    port: int
    debug: bool
    cors_origins: list

@dataclass
class Config:
    """Ana konfigürasyon sınıfı"""
    database: DatabaseConfig
    llm: LLMConfig
    security: SecurityConfig
    server: ServerConfig
    
    # Ek konfigürasyon
    project_root: Path
    data_dir: Path
    logs_dir: Path
    
    @classmethod
    def load_from_env(cls) -> 'Config':
        """Çevre değişkenlerinden konfigürasyonu yükler"""
        try:
            # Proje kök dizinini belirle
            project_root = Path(__file__).parent.parent.parent
            
            # Veritabanı konfigürasyonu
            database = DatabaseConfig(
                database_url=os.getenv("DATABASE_URL", "sqlite:///./kairos.db"),
                neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
                neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
                neo4j_password=os.getenv("NEO4J_PASSWORD", "password"),
                qdrant_host=os.getenv("QDRANT_HOST", "localhost"),
                qdrant_port=int(os.getenv("QDRANT_PORT", "6333")),
                qdrant_collection=os.getenv("QDRANT_COLLECTION", "kairos_memory")
            )
            
            # LLM konfigürasyonu
            llm = LLMConfig(
                openai_api_key=os.getenv("OPENAI_API_KEY"),
                anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                default_model=os.getenv("DEFAULT_MODEL", "gpt-3.5-turbo"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2000"))
            )
            
            # Güvenlik konfigürasyonu
            security = SecurityConfig(
                secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
                jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
                access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
            )
            
            # Sunucu konfigürasyonu
            cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000")
            cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]
            
            server = ServerConfig(
                host=os.getenv("HOST", "127.0.0.1"),
                port=int(os.getenv("PORT", "8000")),
                debug=os.getenv("DEBUG", "false").lower() == "true",
                cors_origins=cors_origins
            )
            
            # Dizin yapısı
            data_dir = project_root / "data"
            logs_dir = project_root / "logs"
            
            # Dizinleri oluştur
            data_dir.mkdir(exist_ok=True)
            logs_dir.mkdir(exist_ok=True)
            
            config = cls(
                database=database,
                llm=llm,
                security=security,
                server=server,
                project_root=project_root,
                data_dir=data_dir,
                logs_dir=logs_dir
            )
            
            logger.info("Konfigürasyon başarıyla yüklendi")
            return config
            
        except Exception as e:
            logger.error(f"Konfigürasyon yüklenirken hata: {e}")
            raise
    
    def validate(self) -> bool:
        """Konfigürasyonun geçerliliğini kontrol eder"""
        errors = []
        
        # LLM API anahtarı kontrolü (sadece uyarı)
        if not self.llm.openai_api_key and not self.llm.anthropic_api_key:
            logger.warning("API anahtarları bulunamadı - sadece yerel modeller (Ollama) kullanılabilir")
        
        # Güvenlik kontrolü
        if self.security.secret_key == "dev-secret-key-change-in-production":
            logger.warning("Üretim ortamında SECRET_KEY değiştirilmeli!")
        
        # Dizin kontrolleri
        if not self.project_root.exists():
            errors.append(f"Proje kök dizini bulunamadı: {self.project_root}")
        
        if errors:
            for error in errors:
                logger.error(f"Konfigürasyon hatası: {error}")
            return False
        
        return True
    
    def get_database_url(self) -> str:
        """Veritabanı URL'sini döndürür"""
        return self.database.database_url
    
    def get_llm_config(self) -> Dict[str, Any]:
        """LLM konfigürasyonunu sözlük olarak döndürür"""
        return {
            "openai_api_key": self.llm.openai_api_key,
            "anthropic_api_key": self.llm.anthropic_api_key,
            "default_model": self.llm.default_model,
            "temperature": self.llm.temperature,
            "max_tokens": self.llm.max_tokens
        }

# Global konfigürasyon nesnesi
_config: Optional[Config] = None

def get_config() -> Config:
    """Global konfigürasyon nesnesini döndürür"""
    global _config
    if _config is None:
        _config = Config.load_from_env()
        if not _config.validate():
            raise ValueError("Konfigürasyon geçersiz")
    return _config

def reload_config() -> Config:
    """Konfigürasyonu yeniden yükler"""
    global _config
    _config = None
    return get_config()
