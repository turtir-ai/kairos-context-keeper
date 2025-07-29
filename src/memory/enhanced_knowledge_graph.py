import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

class EnhancedKnowledgeGraph:
    """Enhanced Knowledge Graph with local storage and extensibility for Neo4j/Qdrant"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # For now, use local storage (can be extended to Neo4j/Qdrant later)
        self.neo4j_available = False
        self.qdrant_available = False
        
        # Local storage
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
        
        self.logger.info("🧠 Enhanced Knowledge Graph initialized (local storage mode)")
        
    def add_node(self, node_id: str, data: Dict[str, Any], node_type: str = "general") -> bool:
        """Add a node to the knowledge graph"""
        try:
            self.local_storage["nodes"][node_id] = {
                "id": node_id,
                "type": node_type,
                "data": data,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            self.stats["nodes_created"] += 1
            self.logger.info(f"✅ Added node {node_id} (type: {node_type})")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add node {node_id}: {e}")
            return False
            
    def add_edge(self, from_node: str, to_node: str, relationship: str, properties: Dict = None) -> bool:
        """Add an edge between two nodes"""
        try:
            if from_node not in self.local_storage["edges"]:
                self.local_storage["edges"][from_node] = []
                
            edge = {
                "to": to_node,
                "relationship": relationship,
                "properties": properties or {},
                "created_at": datetime.now().isoformat()
            }
            
            self.local_storage["edges"][from_node].append(edge)
            self.stats["edges_created"] += 1
            self.logger.info(f"✅ Added edge {from_node} --{relationship}--> {to_node}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add edge {from_node} -> {to_node}: {e}")
            return False
            
    def add_context_memory(self, content: str, context_type: str = "general", metadata: Dict = None) -> str:
        """Add contextual memory with automatic ID generation"""
        import hashlib
        memory_id = hashlib.md5(f"{content}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        try:
            self.local_storage["vectors"][memory_id] = {
                "content": content,
                "context_type": context_type,
                "metadata": metadata or {},
                "created_at": datetime.now().isoformat()
            }
            self.logger.info(f"✅ Added context memory {memory_id} (type: {context_type})")
            return memory_id
        except Exception as e:
            self.logger.error(f"Failed to add context memory: {e}")
            return None
            
    def query_nodes(self, query: str, node_type: str = None, limit: int = 10) -> List[Dict]:
        """Query nodes in the knowledge graph"""
        self.stats["queries_executed"] += 1
        self.stats["last_activity"] = datetime.now().isoformat()
        
        try:
            results = []
            query_lower = query.lower()
            
            for node_id, node_data in self.local_storage["nodes"].items():
                # Filter by type if specified
                if node_type and node_data.get("type") != node_type:
                    continue
                
                # Handle wildcard query
                if query == "*" or not query.strip():
                    # Return all nodes for wildcard
                    results.append({
                        "id": node_id,
                        "type": node_data.get("type", "unknown"),
                        "data": node_data.get("data", {}),
                        "relevance": 1.0,
                        "created_at": node_data.get("created_at"),
                        "relationships": self.get_node_relationships(node_id)
                    })
                else:
                    # Simple text matching in node data
                    content = json.dumps(node_data).lower()
                    if query_lower in content:
                        relevance_score = content.count(query_lower)
                        results.append({
                            "id": node_id,
                            "type": node_data.get("type", "unknown"),
                            "data": node_data.get("data", {}),
                            "relevance": relevance_score,
                            "created_at": node_data.get("created_at"),
                            "relationships": self.get_node_relationships(node_id)
                        })
                
                if len(results) >= limit:
                    break
                        
            # Sort by relevance
            return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            return []
            
    def query_context(self, query: str, context_type: str = None, limit: int = 5) -> List[Dict]:
        """Query context memories"""
        try:
            results = []
            query_lower = query.lower()
            
            for memory_id, memory_data in self.local_storage["vectors"].items():
                # Filter by context type if specified
                if context_type and memory_data.get("context_type") != context_type:
                    continue
                
                # Simple text matching in content
                content = memory_data.get("content", "").lower()
                if query_lower in content:
                    relevance_score = content.count(query_lower)
                    results.append({
                        "id": memory_id,
                        "content": memory_data.get("content"),
                        "context_type": memory_data.get("context_type"),
                        "metadata": memory_data.get("metadata", {}),
                        "relevance": relevance_score,
                        "created_at": memory_data.get("created_at")
                    })
                    
                    if len(results) >= limit:
                        break
                        
            return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)
            
        except Exception as e:
            self.logger.error(f"Context query failed: {e}")
            return []
            
    def get_node_relationships(self, node_id: str) -> List[Dict]:
        """Get all relationships for a node"""
        relationships = []
        
        # Outgoing relationships
        if node_id in self.local_storage["edges"]:
            for edge in self.local_storage["edges"][node_id]:
                relationships.append({
                    "direction": "outgoing",
                    "to": edge["to"],
                    "relationship": edge["relationship"],
                    "properties": edge.get("properties", {}),
                    "created_at": edge.get("created_at")
                })
        
        # Incoming relationships
        for from_node, edges in self.local_storage["edges"].items():
            for edge in edges:
                if edge["to"] == node_id:
                    relationships.append({
                        "direction": "incoming",
                        "from": from_node,
                        "relationship": edge["relationship"],
                        "properties": edge.get("properties", {}),
                        "created_at": edge.get("created_at")
                    })
        
        return relationships
        
    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        return {
            "storage_type": "local",
            "neo4j_available": self.neo4j_available,
            "qdrant_available": self.qdrant_available,
            "stats": self.stats,
            "storage_size": {
                "nodes": len(self.local_storage["nodes"]),
                "edges": sum(len(edges) for edges in self.local_storage["edges"].values()),
                "context_memories": len(self.local_storage["vectors"])
            },
            "node_types": list(set(node.get("type", "unknown") for node in self.local_storage["nodes"].values())),
            "context_types": list(set(mem.get("context_type", "general") for mem in self.local_storage["vectors"].values()))
        }
        
    def export_graph_data(self) -> Dict[str, Any]:
        """Export all graph data for backup or analysis"""
        return {
            "metadata": {
                "exported_at": datetime.now().isoformat(),
                "version": "1.0",
                "stats": self.get_stats()
            },
            "data": self.local_storage
        }
        
    def import_graph_data(self, graph_data: Dict[str, Any]) -> bool:
        """Import graph data from backup"""
        try:
            if "data" in graph_data:
                self.local_storage.update(graph_data["data"])
                self.logger.info("✅ Graph data imported successfully")
                return True
        except Exception as e:
            self.logger.error(f"Failed to import graph data: {e}")
        return False
    
    def query_nodes_optimized(self, query: str, node_type: str = None, limit: int = 10) -> List[Dict]:
        """Optimized version of query_nodes with better indexing and performance"""
        self.stats["queries_executed"] += 1
        self.stats["last_activity"] = datetime.now().isoformat()
        
        try:
            results = []
            query_lower = query.lower()
            
            # Pre-filter by node type if specified for better performance
            if node_type:
                candidate_nodes = {nid: ndata for nid, ndata in self.local_storage["nodes"].items() 
                                 if ndata.get("type") == node_type}
            else:
                candidate_nodes = self.local_storage["nodes"]
            
            # Handle wildcard query efficiently
            if query == "*" or not query.strip():
                for node_id, node_data in list(candidate_nodes.items())[:limit]:
                    results.append({
                        "id": node_id,
                        "type": node_data.get("type", "unknown"),
                        "data": node_data.get("data", {}),
                        "relevance": 1.0,
                        "created_at": node_data.get("created_at"),
                        "relationships": self.get_node_relationships(node_id)
                    })
                return results
            
            # Optimized text search with early termination
            for node_id, node_data in candidate_nodes.items():
                # Skip expensive JSON conversion if possible
                if query_lower in str(node_data.get("data", {})).lower() or \
                   query_lower in node_data.get("type", "").lower():
                    
                    content = json.dumps(node_data).lower()
                    relevance_score = content.count(query_lower)
                    
                    results.append({
                        "id": node_id,
                        "type": node_data.get("type", "unknown"),
                        "data": node_data.get("data", {}),
                        "relevance": relevance_score,
                        "created_at": node_data.get("created_at"),
                        "relationships": self.get_node_relationships(node_id)
                    })
                    
                    # Early termination for performance
                    if len(results) >= limit * 2:  # Get some extra for sorting
                        break
            
            # Sort by relevance and limit results
            return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)[:limit]
            
        except Exception as e:
            self.logger.error(f"Optimized query failed: {e}")
            return []
    
    def query_context_optimized(self, query: str, context_type: str = None, limit: int = 5) -> List[Dict]:
        """Optimized context memory query with pre-filtering"""
        try:
            results = []
            query_lower = query.lower()
            
            # Pre-filter by context type if specified
            if context_type:
                candidate_memories = {mid: mdata for mid, mdata in self.local_storage["vectors"].items() 
                                    if mdata.get("context_type") == context_type}
            else:
                candidate_memories = self.local_storage["vectors"]
            
            # Optimized search with early termination
            for memory_id, memory_data in candidate_memories.items():
                content = memory_data.get("content", "").lower()
                if query_lower in content:
                    relevance_score = content.count(query_lower)
                    results.append({
                        "id": memory_id,
                        "content": memory_data.get("content"),
                        "context_type": memory_data.get("context_type"),
                        "metadata": memory_data.get("metadata", {}),
                        "relevance": relevance_score,
                        "created_at": memory_data.get("created_at")
                    })
                    
                    # Early termination
                    if len(results) >= limit * 2:
                        break
            
            return sorted(results, key=lambda x: x.get("relevance", 0), reverse=True)[:limit]
            
        except Exception as e:
            self.logger.error(f"Optimized context query failed: {e}")
            return []
    
    def add_edges_batch(self, relationships: List[Dict]) -> bool:
        """Batch add relationships for better performance"""
        try:
            for rel in relationships:
                from_node = rel["from"]
                to_node = rel["to"]
                relationship = rel["relationship"]
                properties = rel.get("properties", {})
                
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
            
            self.logger.info(f"✅ Batch added {len(relationships)} relationships")
            return True
            
        except Exception as e:
            self.logger.error(f"Batch relationship addition failed: {e}")
            return False
