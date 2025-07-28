"""
Unified Memory Manager for Kairos Context Keeper
Integrates all memory components into a cohesive system
"""

import json
import logging
import hashlib
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# Import existing memory components
from .context_manager import ContextManager
from .enhanced_knowledge_graph import EnhancedKnowledgeGraph

try:
    from .neo4j_integration import Neo4jKnowledgeGraph
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

try:
    from .qdrant_integration import QdrantVectorStore
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False


class MemoryManager:
    """
    Unified Memory Manager that orchestrates all memory systems:
    - Working Memory (immediate context)
    - Episodic Memory (events and experiences)
    - Semantic Memory (knowledge graph)
    - Context Memory (conversational context)
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the unified memory system"""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize memory components
        self._init_components()
        
        # Memory statistics
        self.stats = {
            "initialized_at": datetime.now().isoformat(),
            "operations_count": 0,
            "last_activity": datetime.now().isoformat(),
            "memory_layers": {
                "working": {"enabled": True, "items": 0},
                "episodic": {"enabled": True, "items": 0},
                "semantic": {"enabled": True, "items": 0},
                "context": {"enabled": True, "items": 0}
            }
        }
        
        self.logger.info("🧠 Unified Memory Manager initialized successfully")
    
    def _init_components(self):
        """Initialize all memory components"""
        
        # 1. Working Memory & Context Manager
        self.context_manager = ContextManager()
        
        # 2. Knowledge Graph - Try Neo4j first, fallback to Enhanced local
        if NEO4J_AVAILABLE and self.config.get("use_neo4j", True):
            try:
                self.knowledge_graph = Neo4jKnowledgeGraph()
                if self.knowledge_graph.connected:
                    self.semantic_storage = "neo4j"
                    self.logger.info("✅ Using Neo4j for semantic memory")
                else:
                    raise Exception("Neo4j connection failed")
            except Exception as e:
                self.logger.warning(f"Neo4j unavailable, falling back to local storage: {e}")
                self.knowledge_graph = EnhancedKnowledgeGraph()
                self.semantic_storage = "local"
        else:
            self.knowledge_graph = EnhancedKnowledgeGraph()
            self.semantic_storage = "local"

        # Setup Qdrant integration
        if QDRANT_AVAILABLE and self.config.get("use_qdrant", True):
            try:
                self.qdrant_client = QdrantVectorStore(
                    host=self.config.get("qdrant_host", "localhost"), 
                    port=self.config.get("qdrant_port", 6333),
                    collection_name="kairos_memory"
                )
                if self.qdrant_client.available:
                    self.vector_storage = "qdrant"
                    self.logger.info("✅ Using Qdrant for vector storage")
                else:
                    raise Exception("Qdrant connection failed")
            except Exception as e:
                self.logger.warning(f"Qdrant unavailable, falling back to local storage: {e}")
                self.vector_storage = "local"
                self.qdrant_client = None
        else:
            self.vector_storage = "local"
            self.qdrant_client = None
        
        # 3. Episodic Memory - Integrated with context manager
        self.episodic_memory = []  # Will be managed by context_manager
        
        # 4. Long-term persistence
        self.persistence_path = Path(self.config.get("persistence_path", "data/memory"))
        self.persistence_path.mkdir(parents=True, exist_ok=True)
    
    # ========== WORKING MEMORY OPERATIONS ==========
    
    def update_working_memory(self, key: str, value: Any, metadata: Dict = None) -> bool:
        """Update working memory with immediate context"""
        try:
            self.context_manager.update(key, value)
            
            # Add metadata if provided
            if metadata:
                self.context_manager.update(f"{key}_metadata", metadata)
            
            self.stats["memory_layers"]["working"]["items"] += 1
            self._update_activity()
            
            self.logger.info(f"✅ Working memory updated: {key}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update working memory {key}: {e}")
            return False
    
    def get_working_memory(self, key: str, default=None) -> Any:
        """Retrieve from working memory"""
        try:
            value = self.context_manager.get(key, default)
            self._update_activity()
            return value
        except Exception as e:
            self.logger.error(f"Failed to get working memory {key}: {e}")
            return default
    
    def get_working_memory_summary(self) -> Dict[str, Any]:
        """Get summary of working memory"""
        return self.context_manager.summarize_context()
    
    # ========== EPISODIC MEMORY OPERATIONS ==========
    
    def add_episode(self, episode_type: str, content: str, metadata: Dict = None) -> str:
        """Add an episode to episodic memory"""
        try:
            episode_id = hashlib.md5(f"{episode_type}_{content}_{datetime.now()}".encode()).hexdigest()[:12]
            
            episode = {
                "id": episode_id,
                "type": episode_type,
                "content": content,
                "metadata": metadata or {},
                "timestamp": datetime.now().isoformat()
            }
            
            # Add to context manager's episodic memory
            self.context_manager.add_episode(episode)
            
            # Also store in knowledge graph for semantic connections
            self.knowledge_graph.add_node(
                node_id=f"episode_{episode_id}",
                data=episode,
                node_type="episode"
            )
            
            self.stats["memory_layers"]["episodic"]["items"] += 1
            self._update_activity()
            
            self.logger.info(f"✅ Episode added: {episode_type} ({episode_id})")
            return episode_id
            
        except Exception as e:
            self.logger.error(f"Failed to add episode: {e}")
            return None
    
    def get_recent_episodes(self, limit: int = 10, episode_type: str = None) -> List[Dict]:
        """Get recent episodes, optionally filtered by type"""
        try:
            episodes = self.context_manager.get_recent_episodes(limit * 2)  # Get more for filtering
            
            if episode_type:
                episodes = [ep for ep in episodes if ep.get("type") == episode_type]
            
            return episodes[:limit]
        except Exception as e:
            self.logger.error(f"Failed to get recent episodes: {e}")
            return []
    
    def search_episodes(self, query: str, limit: int = 5) -> List[Dict]:
        """Search episodes by content"""
        try:
            # Search in knowledge graph
            results = self.knowledge_graph.query_nodes(query, node_type="episode", limit=limit)
            
            episodes = []
            for result in results:
                if "data" in result:
                    episodes.append(result["data"])
            
            return episodes
        except Exception as e:
            self.logger.error(f"Failed to search episodes: {e}")
            return []
    
    # ========== SEMANTIC MEMORY OPERATIONS ==========
    
    def add_knowledge_node(self, node_id: str, data: Dict[str, Any], node_type: str = "concept") -> bool:
        """Add a knowledge node to semantic memory"""
        try:
            success = self.knowledge_graph.add_node(node_id, data, node_type)
            if success:
                self.stats["memory_layers"]["semantic"]["items"] += 1
                self._update_activity()
            return success
        except Exception as e:
            self.logger.error(f"Failed to add knowledge node {node_id}: {e}")
            return False
    
    def add_knowledge_relationship(self, from_node: str, to_node: str, relationship: str, properties: Dict = None) -> bool:
        """Add a relationship between knowledge nodes"""
        try:
            return self.knowledge_graph.add_edge(from_node, to_node, relationship, properties)
        except Exception as e:
            self.logger.error(f"Failed to add relationship {from_node} -> {to_node}: {e}")
            return False
    
    def search_knowledge(self, query: str, node_type: str = None, limit: int = 10) -> List[Dict]:
        """Search semantic knowledge"""
        try:
            self._update_activity()
            return self.knowledge_graph.query_nodes(query, node_type, limit)
        except Exception as e:
            self.logger.error(f"Knowledge search failed: {e}")
            return []
    
    def get_node_context(self, node_id: str) -> Dict[str, Any]:
        """Get full context for a knowledge node including relationships"""
        try:
            relationships = self.knowledge_graph.get_node_relationships(node_id)
            return {
                "node_id": node_id,
                "relationships": relationships,
                "relationship_count": len(relationships)
            }
        except Exception as e:
            self.logger.error(f"Failed to get node context for {node_id}: {e}")
            return {"node_id": node_id, "relationships": [], "relationship_count": 0}
    
    # ========== CONTEXT MEMORY OPERATIONS ==========
    
    def add_context_memory(self, content: str, context_type: str = "conversation", metadata: Dict = None) -> str:
        """Add contextual memory for semantic search"""
        try:
            memory_id = self.knowledge_graph.add_context_memory(content, context_type, metadata)
            if memory_id:
                self.stats["memory_layers"]["context"]["items"] += 1
                self._update_activity()
            return memory_id
        except Exception as e:
            self.logger.error(f"Failed to add context memory: {e}")
            return None
    
    def search_context_memory(self, query: str, context_type: str = None, limit: int = 5) -> List[Dict]:
        """Search context memory"""
        try:
            self._update_activity()
            
            # Check if knowledge_graph has query_context method, if not use query_nodes
            if hasattr(self.knowledge_graph, 'query_context'):
                return self.knowledge_graph.query_context(query, context_type, limit)
            else:
                # Fallback to searching nodes with context filter
                results = self.knowledge_graph.query_nodes(query, "memory", limit)
                # Filter by context_type if provided
                if context_type:
                    results = [r for r in results if r.get('data', {}).get('context_type') == context_type]
                return results
        except Exception as e:
            self.logger.error(f"Context memory search failed: {e}")
            return []
    
    # ========== INTEGRATED OPERATIONS ==========
    
    def store_conversation_turn(self, role: str, content: str, metadata: Dict = None) -> Dict[str, str]:
        """Store a complete conversation turn across all memory layers"""
        try:
            turn_id = hashlib.md5(f"{role}_{content}_{datetime.now()}".encode()).hexdigest()[:12]
            
            # 1. Add to working memory
            self.update_working_memory(f"last_{role}_message", content, metadata)
            
            # 2. Add as episode
            episode_id = self.add_episode("conversation_turn", content, {
                "role": role,
                "turn_id": turn_id,
                **(metadata or {})
            })
            
            # 3. Add to context memory for semantic search
            context_id = self.add_context_memory(content, "conversation", {
                "role": role,
                "turn_id": turn_id,
                "episode_id": episode_id,
                **(metadata or {})
            })
            
            # 4. Create knowledge connections if this relates to existing concepts
            self._create_semantic_connections(content, turn_id, role)
            
            return {
                "turn_id": turn_id,
                "episode_id": episode_id,
                "context_id": context_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to store conversation turn: {e}")
            return {}
    
    def recall_relevant_context(self, query: str, limit: int = 10) -> Dict[str, List[Dict]]:
        """Recall relevant information from all memory layers"""
        try:
            context = {
                "working_memory": self.get_working_memory_summary(),
                "recent_episodes": self.get_recent_episodes(5),
                "semantic_knowledge": self.search_knowledge(query, limit=limit//2),
                "context_memories": self.search_context_memory(query, limit=limit//2),
                "query": query,
                "recalled_at": datetime.now().isoformat()
            }
            
            self._update_activity()
            return context
            
        except Exception as e:
            self.logger.error(f"Failed to recall context: {e}")
            return {"error": str(e), "query": query}
    
    def _create_semantic_connections(self, content: str, turn_id: str, role: str):
        """Create semantic connections between conversation and existing knowledge"""
        try:
            # Simple keyword-based connections (can be enhanced with NLP)
            keywords = [word.lower().strip('.,!?";') for word in content.split() if len(word) > 3]
            
            # Search for existing nodes that might relate
            for keyword in keywords[:5]:  # Limit to avoid too many connections
                related_nodes = self.search_knowledge(keyword, limit=3)
                for node in related_nodes:
                    # Create relationship from conversation turn to related concept
                    self.add_knowledge_relationship(
                        f"turn_{turn_id}",
                        node["id"], 
                        "mentions",
                        {"keyword": keyword, "role": role}
                    )
                    
        except Exception as e:
            self.logger.debug(f"Semantic connection creation failed: {e}")
    
    # ========== PERSISTENCE OPERATIONS ==========
    
    def save_memory_state(self, filename: str = None) -> bool:
        """Save current memory state to disk"""
        try:
            if not filename:
                filename = f"memory_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filepath = self.persistence_path / filename
            
            memory_state = {
                "saved_at": datetime.now().isoformat(),
                "stats": self.stats,
                "working_memory": self.context_manager.export_context(),
                "knowledge_graph": self.knowledge_graph.export_graph_data() if hasattr(self.knowledge_graph, 'export_graph_data') else None,
                "semantic_storage": self.semantic_storage
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(memory_state, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"✅ Memory state saved to {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save memory state: {e}")
            return False
    
    def load_memory_state(self, filename: str) -> bool:
        """Load memory state from disk"""
        try:
            filepath = self.persistence_path / filename
            
            if not filepath.exists():
                self.logger.error(f"Memory state file not found: {filepath}")
                return False
            
            with open(filepath, 'r', encoding='utf-8') as f:
                memory_state = json.load(f)
            
            # Restore knowledge graph data if available
            if memory_state.get("knowledge_graph") and hasattr(self.knowledge_graph, 'import_graph_data'):
                self.knowledge_graph.import_graph_data(memory_state["knowledge_graph"])
            
            self.logger.info(f"✅ Memory state loaded from {filepath}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to load memory state: {e}")
            return False
    
    # ========== UTILITY METHODS ==========
    
    def _update_activity(self):
        """Update activity timestamp and operation count"""
        self.stats["last_activity"] = datetime.now().isoformat()
        self.stats["operations_count"] += 1
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        try:
            # Get knowledge graph stats
            kg_stats = self.knowledge_graph.get_stats()
            
            return {
                "manager_stats": self.stats,
                "knowledge_graph_stats": kg_stats,
                "semantic_storage": self.semantic_storage,
                "persistence_path": str(self.persistence_path),
                "neo4j_available": NEO4J_AVAILABLE,
                "total_memory_items": sum(
                    layer["items"] for layer in self.stats["memory_layers"].values()
                )
            }
        except Exception as e:
            self.logger.error(f"Failed to get memory stats: {e}")
            return {"error": str(e)}
    
    def clear_memory(self, layer: str = "all") -> bool:
        """Clear specific memory layer or all memory"""
        try:
            if layer in ["working", "all"]:
                self.context_manager = ContextManager()
                self.stats["memory_layers"]["working"]["items"] = 0
            
            if layer in ["episodic", "all"]:
                self.episodic_memory = []
                self.stats["memory_layers"]["episodic"]["items"] = 0
            
            if layer in ["semantic", "all"]:
                # Reinitialize knowledge graph
                self._init_components()
                self.stats["memory_layers"]["semantic"]["items"] = 0
            
            if layer in ["context", "all"]:
                # Context memory is part of knowledge graph
                self.stats["memory_layers"]["context"]["items"] = 0
            
            self.logger.info(f"✅ Cleared {layer} memory layer(s)")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear {layer} memory: {e}")
            return False
    
    def close(self):
        """Properly close all memory components"""
        try:
            if hasattr(self.knowledge_graph, 'close'):
                self.knowledge_graph.close()
            self.logger.info("🧠 Memory Manager closed successfully")
        except Exception as e:
            self.logger.error(f"Error closing Memory Manager: {e}")


# Factory function for easy initialization
def create_memory_manager(config: Dict[str, Any] = None) -> MemoryManager:
    """Factory function to create and initialize MemoryManager"""
    return MemoryManager(config)
