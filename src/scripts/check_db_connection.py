#!/usr/bin/env python3
"""
Kairos Database Connection Test
Tests connectivity to all required database services
"""

import os
import sys
import sqlite3
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def check_sqlite_connection():
    """Test SQLite database connection"""
    try:
        database_url = os.getenv("DATABASE_URL", "sqlite:///kairos_dev.db")
        if database_url.startswith("sqlite:///"):
            db_path = database_url.replace("sqlite:///", "")
            # Create database directory if it doesn't exist
            db_dir = Path(db_path).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            
            # Test connection
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT sqlite_version();")
            version = cursor.fetchone()[0]
            conn.close()
            print(f"✅ SQLite bağlantısı başarılı! (Version: {version})")
            return True
    except Exception as e:
        print(f"❌ SQLite bağlantı hatası: {e}")
        return False

def check_neo4j_connection():
    """Test Neo4j database connection (optional)"""
    neo4j_uri = os.getenv("NEO4J_URI")
    if not neo4j_uri:
        print("ℹ️  Neo4j devre dışı (development mode)")
        return True
        
    try:
        from neo4j import GraphDatabase
        user = os.getenv("NEO4J_USER", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "password")
        driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
        driver.verify_connectivity()
        driver.close()
        print("✅ Neo4j bağlantısı başarılı!")
        return True
    except ImportError:
        print("⚠️  Neo4j driver yüklü değil (optional)")
        return True
    except Exception as e:
        print(f"❌ Neo4j bağlantı hatası: {e}")
        return False

def check_qdrant_connection():
    """Test Qdrant vector database connection (optional)"""
    qdrant_host = os.getenv("QDRANT_HOST")
    if not qdrant_host:
        print("ℹ️  Qdrant devre dışı (development mode)")
        return True
        
    try:
        from qdrant_client import QdrantClient
        port = int(os.getenv("QDRANT_PORT", "6333"))
        client = QdrantClient(host=qdrant_host, port=port)
        client.get_collections()
        print("✅ Qdrant bağlantısı başarılı!")
        return True
    except ImportError:
        print("⚠️  Qdrant client yüklü değil (optional)")
        return True
    except Exception as e:
        print(f"❌ Qdrant bağlantı hatası: {e}")
        return False

def check_redis_connection():
    """Test Redis connection (optional)"""
    redis_host = os.getenv("REDIS_HOST")
    if not redis_host:
        print("ℹ️  Redis devre dışı (development mode)")
        return True
        
    try:
        import redis
        port = int(os.getenv("REDIS_PORT", "6379"))
        r = redis.Redis(host=redis_host, port=port, decode_responses=True)
        r.ping()
        print("✅ Redis bağlantısı başarılı!")
        return True
    except ImportError:
        print("⚠️  Redis client yüklü değil (optional)")
        return True
    except Exception as e:
        print(f"❌ Redis bağlantı hatası: {e}")
        return False

def main():
    """Run all database connection tests"""
    print("🔍 Kairos Database Connection Test")
    print("=" * 50)
    
    results = []
    results.append(check_sqlite_connection())
    results.append(check_neo4j_connection())
    results.append(check_qdrant_connection())
    results.append(check_redis_connection())
    
    print("\n" + "=" * 50)
    if all(results):
        print("🎉 Tüm veritabanı bağlantıları başarılı!")
        return 0
    else:
        print("⚠️  Bazı bağlantılar başarısız oldu, ama geliştirme için devam edilebilir.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
