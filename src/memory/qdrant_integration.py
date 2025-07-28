import logging
import hashlib
import numpy as np
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

# Import WebSocket manager for real-time broadcasting
try:
    from ..api.websocket_manager import WebSocketManager
except ImportError:
    WebSocketManager = None


class QdrantVectorStore:
    """Qdrant Vector Database Integration for Semantic Memory Storage"""
    
    def __init__(self, host=None, port=None, collection_name="kairos_memory", websocket_manager=None):
        self.logger = logging.getLogger(__name__)
        self.collection_name = collection_name
        self.websocket_manager = websocket_manager
        
        # Get connection details from environment variables
        host = host or os.getenv("QDRANT_HOST", "localhost")
        port = port or int(os.getenv("QDRANT_PORT", "6333"))
        
        # Initialize embedding model first (needed for collection setup)
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            self.logger.info(f"✅ Embedding model loaded, dimension: {self.embedding_dim}")
        except Exception as e:
            self.logger.error(f"❌ Failed to load embedding model: {e}")
            self.embedding_model = None
            self.embedding_dim = 384  # Fallback dimension
            
        # Then initialize Qdrant connection
        try:
            self.client = QdrantClient(host=host, port=port)
            self.available = True
            self._ensure_collection_exists()
            self.logger.info("✅ Qdrant vector store initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to connect to Qdrant: {e}")
            self.client = None
            self.available = False
            
        # Stats tracking
        self.stats = {
            "vectors_stored": 0,
            "searches_performed": 0,
            "last_activity": datetime.now().isoformat()
        }
    
    def _ensure_collection_exists(self):
        """Ensure the Qdrant collection exists with proper configuration"""
        if not self.available:
            return False
            
        try:
            collections = self.client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                self.logger.info(f"✅ Created collection: {self.collection_name}")
                return True
            else:
                self.logger.info(f"✅ Collection already exists: {self.collection_name}")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Failed to ensure collection exists: {e}")
            return False
    
    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text"""
        if self.embedding_model:
            try:
                embedding = self.embedding_model.encode(text)
                return embedding.tolist()
            except Exception as e:
                self.logger.error(f"❌ Failed to generate embedding: {e}")
                
        # Fallback: random vector (for testing/demo purposes)
        self.logger.warning("Using random embedding as fallback")
        return np.random.rand(self.embedding_dim).tolist()
    
    def add_memory(
        self,
        content: str,
        metadata: Dict[str, Any] = None,
        memory_id: str = None,
        agent_id: str = None,
        memory_type: str = "general"
    ) -> Optional[str]:
        """Add a memory with semantic embedding"""
        if not self.available:
            self.logger.warning("Qdrant not available, cannot add memory")
            return None
            
        try:
            # Generate unique ID if not provided
            if not memory_id:
                memory_id = hashlib.md5(f"{content}{datetime.now().isoformat()}".encode()).hexdigest()
            
            # Generate embedding
            vector = self._generate_embedding(content)
            
            # Prepare metadata
            payload = {
                "content": content,
                "memory_type": memory_type,
                "agent_id": agent_id or "system",
                "created_at": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Create point
            point = PointStruct(
                id=memory_id,
                vector=vector,
                payload=payload
            )
            
            # Insert into Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            self.stats["vectors_stored"] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            
            # Broadcast memory addition via WebSocket
            if self.websocket_manager:
                try:
                    self.websocket_manager.broadcast_to_subscribers(
                        "memory_updates",
                        {
                            "type": "memory_added",
                            "memory_id": memory_id,
                            "content": content[:200] + "..." if len(content) > 200 else content,
                            "memory_type": memory_type,
                            "agent_id": agent_id or "system",
                            "embedding_dim": len(vector),
                            "timestamp": datetime.now().isoformat(),
                            "stats": self.stats.copy()
                        }
                    )
                except Exception as ws_e:
                    self.logger.warning(f"Failed to broadcast memory addition: {ws_e}")
            
            self.logger.info(f"✅ Added memory {memory_id} to Qdrant")
            return memory_id
            
        except Exception as e:
            self.logger.error(f"❌ Failed to add memory: {e}")
            return None
    
    def search_similar(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        filter_conditions: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """Search for semantically similar memories"""
        if not self.available:
            self.logger.warning("Qdrant not available, cannot search")
            return []
            
        try:
            # Generate query embedding
            query_vector = self._generate_embedding(query)
            
            # Prepare filter if provided
            filter_obj = None
            if filter_conditions:
                conditions = []
                for key, value in filter_conditions.items():
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
                filter_obj = Filter(must=conditions)
            
            # Perform search
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold,
                query_filter=filter_obj
            )
            
            # Format results
            results = []
            for scored_point in search_result:
                result = {
                    "id": scored_point.id,
                    "score": scored_point.score,
                    "content": scored_point.payload.get("content", ""),
                    "memory_type": scored_point.payload.get("memory_type", "general"),
                    "agent_id": scored_point.payload.get("agent_id", "unknown"),
                    "created_at": scored_point.payload.get("created_at", ""),
                    "metadata": scored_point.payload.get("metadata", {})
                }
                results.append(result)
            
            self.stats["searches_performed"] += 1
            self.stats["last_activity"] = datetime.now().isoformat()
            
            # Broadcast search activity via WebSocket
            if self.websocket_manager and results:
                try:
                    self.websocket_manager.broadcast_to_subscribers(
                        "memory_updates",
                        {
                            "type": "memory_search",
                            "query": query[:100] + "..." if len(query) > 100 else query,
                            "results_count": len(results),
                            "score_threshold": score_threshold,
                            "top_score": results[0]["score"] if results else 0,
                            "timestamp": datetime.now().isoformat(),
                            "stats": self.stats.copy()
                        }
                    )
                except Exception as ws_e:
                    self.logger.warning(f"Failed to broadcast memory search: {ws_e}")
            
            self.logger.info(f"✅ Found {len(results)} similar memories")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Failed to search memories: {e}")
            return []
    
    def search_by_agent(
        self,
        agent_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve all memories for a specific agent"""
        return self.search_similar(
            query="",  # Empty query for all results
            limit=limit,
            score_threshold=0.0,  # No threshold
            filter_conditions={"agent_id": agent_id}
        )
    
    def search_by_type(
        self,
        memory_type: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve memories by type"""
        return self.search_similar(
            query="",
            limit=limit,
            score_threshold=0.0,
            filter_conditions={"memory_type": memory_type}
        )
    
    def delete_memory(self, memory_id: str) -> bool:
        """Delete a specific memory"""
        if not self.available:
            return False
            
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[memory_id]
            )
            
            # Broadcast memory deletion via WebSocket
            if self.websocket_manager:
                try:
                    self.websocket_manager.broadcast_to_subscribers(
                        "memory_updates",
                        {
                            "type": "memory_deleted",
                            "memory_id": memory_id,
                            "timestamp": datetime.now().isoformat(),
                            "stats": self.stats.copy()
                        }
                    )
                except Exception as ws_e:
                    self.logger.warning(f"Failed to broadcast memory deletion: {ws_e}")
            
            self.logger.info(f"✅ Deleted memory {memory_id}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Failed to delete memory {memory_id}: {e}")
            return False
    
    def delete_agent_memories(self, agent_id: str) -> int:
        """Delete all memories for a specific agent"""
        if not self.available:
            return 0
            
        try:
            # Get all memories for agent
            memories = self.search_by_agent(agent_id)
            memory_ids = [m["id"] for m in memories]
            
            if memory_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=memory_ids
                )
                
            # Broadcast bulk deletion via WebSocket
            if self.websocket_manager and memory_ids:
                try:
                    self.websocket_manager.broadcast_to_subscribers(
                        "memory_updates",
                        {
                            "type": "agent_memories_deleted",
                            "agent_id": agent_id,
                            "deleted_count": len(memory_ids),
                            "memory_ids": memory_ids[:10],  # Only send first 10 IDs to avoid large payloads
                            "timestamp": datetime.now().isoformat(),
                            "stats": self.stats.copy()
                        }
                    )
                except Exception as ws_e:
                    self.logger.warning(f"Failed to broadcast agent memory deletion: {ws_e}")
            
            self.logger.info(f"✅ Deleted {len(memory_ids)} memories for agent {agent_id}")
            return len(memory_ids)
            
        except Exception as e:
            self.logger.error(f"❌ Failed to delete agent memories: {e}")
            return 0
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get information about the collection"""
        if not self.available:
            return {"available": False}
            
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "available": True,
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status,
                "optimizer_status": info.optimizer_status,
                "stats": self.stats
            }
        except Exception as e:
            self.logger.error(f"❌ Failed to get collection info: {e}")
            return {"available": False, "error": str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on Qdrant connection"""
        try:
            if not self.available:
                return {"status": "unhealthy", "reason": "Not connected"}
                
            # Try a simple operation
            collections = self.client.get_collections()
            
            return {
                "status": "healthy",
                "collections": len(collections.collections),
                "target_collection": self.collection_name,
                "embedding_model": "all-MiniLM-L6-v2" if self.embedding_model else "fallback",
                "stats": self.stats
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "reason": str(e)
            }
    
    def close(self):
        """Close the Qdrant connection"""
        if self.client:
            # Qdrant client doesn't require explicit closing
            self.logger.info("✅ Qdrant connection closed")
