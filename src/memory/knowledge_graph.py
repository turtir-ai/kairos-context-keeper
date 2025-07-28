import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib
import numpy as np

class KnowledgeGraph:
    """Enhanced Knowledge Graph with Neo4j and Qdrant integration"""
    
    def __init__(self, neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="kairos"):
        self.logger = logging.getLogger(__name__)
        
        # Neo4j connection
        try:
            self.neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
            self.neo4j_available = True
            self.logger.info("✅ Neo4j connection established")
        except Exception as e:
            self.logger.warning(f"⚠️ Neo4j not available, using local storage: {e}")
            self.neo4j_driver = None
            self.neo4j_available = False
            
        # Qdrant connection
        try:
            self.qdrant_client = QdrantClient(host="localhost", port=6333)
            self.collection_name = "kairos_memory"
            self.qdrant_available = True
            self._ensure_collection_exists()
            self.logger.info("✅ Qdrant connection established")
        except Exception as e:
            self.logger.warning(f"⚠️ Qdrant not available, using local storage: {e}")
            self.qdrant_client = None
            self.qdrant_available = False
            
        # Fallback local storage
        self.local_storage = {
            "nodes": {},
            "edges": {},
            "vectors": {},
            "metadata": {}
        }
        
        self.stats = {
            "nodes_created": 0,
            "edges_created": 0,
            "queries_executed": 0,
            "last_activity": datetime.now().isoformat()
        }
        
    def _ensure_collection_exists(self):
        """Ensure Qdrant collection exists"""
        if not self.qdrant_available:
            return
            
        try:
            collections = self.qdrant_client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if self.collection_name not in collection_names:
                self.qdrant_client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
                )
                self.logger.info(f"Created Qdrant collection: {self.collection_name}")
        except Exception as e:
            self.logger.error(f"Failed to ensure Qdrant collection: {e}")
            
    def add_node(self, node_id: str, data: Dict[str, Any], node_type: str = "general") -> bool:
        """Add a node to the knowledge graph"""
        try:
            if self.neo4j_available:
                return self._add_node_neo4j(node_id, data, node_type)
            else:
                return self._add_node_local(node_id, data, node_type)
        except Exception as e:
            self.logger.error(f"Failed to add node {node_id}: {e}")
            return False
            
    def _add_node_neo4j(self, node_id: str, data: Dict, node_type: str) -> bool:
        """Add node using Neo4j"""
        with self.neo4j_driver.session() as session:
            query = """
            MERGE (n:Node {id: $node_id, type: $node_type})
            SET n.data = $data, n.updated_at = $timestamp
            RETURN n
            """
            
            result = session.run(query, 
                node_id=node_id,
                node_type=node_type, 
                data=json.dumps(data),
                timestamp=datetime.now().isoformat()
            )
            
            if result.single():
                self.stats["nodes_created"] += 1
                self.logger.info(f"✅ Added node {node_id} to Neo4j")
                return True
        return False
        
    def _add_node_local(self, node_id: str, data: Dict, node_type: str) -> bool:
        """Add node using local storage"""
        self.local_storage["nodes"][node_id] = {
            "id": node_id,
            "type": node_type,
            "data": data,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        self.stats["nodes_created"] += 1
        self.logger.info(f"✅ Added node {node_id} to local storage")
        return True
        
    def add_edge(self, from_node: str, to_node: str, relationship: str, properties: Dict = None) -> bool:
        """Add an edge between two nodes"""
        try:
            if self.neo4j_available:
                return self._add_edge_neo4j(from_node, to_node, relationship, properties or {})
            else:
                return self._add_edge_local(from_node, to_node, relationship, properties or {})
        except Exception as e:
            self.logger.error(f"Failed to add edge {from_node} - {to_node}: {e}")
            return False
            
    def _add_edge_neo4j(self, from_node: str, to_node: str, relationship: str, properties: Dict) -> bool:
        """Add edge using Neo4j"""
        with self.neo4j_driver.session() as session:
            query = """
            MATCH (a:Node {id: $from_node})
            MATCH (b:Node {id: $to_node})
            MERGE (a)-[r:RELATES {type: $relationship}]-(b)
            SET r.properties = $properties, r.created_at = $timestamp
            RETURN r
            """
            
            result = session.run(query,
                from_node=from_node,
                to_node=to_node, 
                relationship=relationship,
                properties=json.dumps(properties),
                timestamp=datetime.now().isoformat()
            )
            
            if result.single():
                self.stats["edges_created"] += 1
                self.logger.info(f"✅ Added edge {from_node} - {to_node}")
                return True
        return False
        
    def _add_edge_local(self, from_node: str, to_node: str, relationship: str, properties: Dict) -> bool:
        """Add edge using local storage"""
        if from_node not in self.local_storage["edges"]:
            self.local_storage["edges"][from_node] = []
            
        edge = {
            "to": to_node,
            "relationship": relationship,
            "properties": properties,
            "created_at": datetime.now().isoformat()
        }
        
        self.local_storage["edges"][from_node].append(edge)
        self.stats["edges_created"] += 1
        self.logger.info(f"✅ Added edge {from_node} - {to_node} to local storage")
        return True
        
    def add_vector_memory(self, content: str, metadata: Dict = None, vector_id: str = None) -> Optional[str]:
        """Add content with vector embedding for semantic search"""
        if not vector_id:
            vector_id = hashlib.md5(content.encode()).hexdigest()
            
        try:
            if self.qdrant_available:
                return self._add_vector_qdrant(vector_id, content, metadata or {})
            else:
                return self._add_vector_local(vector_id, content, metadata or {})
        except Exception as e:
            self.logger.error(f"Failed to add vector memory: {e}")
            return None
            
    def _add_vector_qdrant(self, vector_id: str, content: str, metadata: Dict) -> str:
        """Add vector using Qdrant"""
        # Simple mock embedding (in real implementation, use proper embedding model)
        vector = np.random.rand(384).tolist()  # Mock 384-dim vector
        
        point = PointStruct(
            id=vector_id,
            vector=vector,
            payload={
                "content": content,
                "metadata": metadata,
                "created_at": datetime.now().isoformat()
            }
        )
        
        self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[point]
        )
        
        self.logger.info(f"✅ Added vector {vector_id} to Qdrant")
        return vector_id
        
    def _add_vector_local(self, vector_id: str, content: str, metadata: Dict) -> str:
        """Add vector using local storage"""
        self.local_storage["vectors"][vector_id] = {
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        self.logger.info(f"✅ Added vector {vector_id} to local storage")
        return vector_id
        
    def query_graph(self, query: str, limit: int = 10) -> List[Dict]:
        """Query the knowledge graph"""
        self.stats["queries_executed"] += 1
        self.stats["last_activity"] = datetime.now().isoformat()
        
        try:
            if self.neo4j_available:
                return self._query_neo4j(query, limit)
            else:
                return self._query_local(query, limit)
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return []
            
    def _query_neo4j(self, query_text: str, limit: int) -> List[Dict]:
        """Query using Neo4j"""
        with self.neo4j_driver.session() as session:
            # Simple text-based search (in real implementation, use full-text indexing)
            query = """
            MATCH (n:Node)
            WHERE n.data CONTAINS $query_text
            RETURN n.id as id, n.type as type, n.data as data
            LIMIT $limit
            """
            
            result = session.run(query, query_text=query_text, limit=limit)
            
            nodes = []
            for record in result:
                nodes.append({
                    "id": record["id"],
                    "type": record["type"], 
                    "data": json.loads(record["data"]) if record["data"] else {}
                })
                
            return nodes
            
    def _query_local(self, query_text: str, limit: int) -> List[Dict]:
        """Query using local storage"""
        results = []
        query_lower = query_text.lower()
        
        for node_id, node_data in self.local_storage["nodes"].items():
            # Simple text matching
            content = json.dumps(node_data).lower()
            if query_lower in content:
                results.append({
                    "id": node_id,
                    "type": node_data.get("type", "unknown"),
                    "data": node_data.get("data", {}),
                    "relevance": content.count(query_lower)  # Simple relevance scoring
                })
                
                if len(results) >= limit:
                    break
                    
        return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
        
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        return {
            "neo4j_available": self.neo4j_available,
            "qdrant_available": self.qdrant_available,
            "stats": self.stats,
            "local_storage_size": {
                "nodes": len(self.local_storage["nodes"]),
                "edges": sum(len(edges) for edges in self.local_storage["edges"].values()),
                "vectors": len(self.local_storage["vectors"])
            }
        }
        
    def close(self):
        """Close connections"""
        if self.neo4j_driver:
            self.neo4j_driver.close()
        if self.qdrant_client:
            # Qdrant client doesn't need explicit closing
            pass
