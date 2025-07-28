import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from neo4j import GraphDatabase
import hashlib
import asyncio

class Neo4jKnowledgeGraph:
    """Neo4j-based Knowledge Graph implementation with real-time WebSocket broadcasting"""
    
    def __init__(self, websocket_manager=None):
        self.logger = logging.getLogger(__name__)
        self.driver = None
        self.connected = False
        self.websocket_manager = websocket_manager
        
        # Connection configuration from environment
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "KairosSecure2025!")
        
        self._connect()
        
    def _connect(self):
        """Establish connection to Neo4j"""
        try:
            self.driver = GraphDatabase.driver(
                self.uri, 
                auth=(self.username, self.password),
                max_connection_lifetime=30 * 60,
                max_connection_pool_size=50,
                connection_acquisition_timeout=2 * 60
            )
            
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
                
            self.connected = True
            self.logger.info("🔌 Connected to Neo4j successfully!")
            
            # Create initial indexes and constraints
            self._setup_schema()
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            self.connected = False
            
    def _setup_schema(self):
        """Setup Neo4j schema with constraints and indexes"""
        try:
            with self.driver.session() as session:
                # Create constraints
                session.run("CREATE CONSTRAINT kairos_node_id IF NOT EXISTS FOR (n:KairosNode) REQUIRE n.node_id IS UNIQUE")
                session.run("CREATE CONSTRAINT kairos_memory_id IF NOT EXISTS FOR (m:KairosMemory) REQUIRE m.memory_id IS UNIQUE")
                
                # Create indexes for performance
                session.run("CREATE INDEX kairos_node_type IF NOT EXISTS FOR (n:KairosNode) ON (n.node_type)")
                session.run("CREATE INDEX kairos_memory_type IF NOT EXISTS FOR (m:KairosMemory) ON (m.context_type)")
                session.run("CREATE INDEX kairos_timestamp IF NOT EXISTS FOR (n:KairosNode) ON (n.created_at)")
                
                self.logger.info("✅ Neo4j schema setup completed")
                
        except Exception as e:
            self.logger.warning(f"Schema setup issue (may already exist): {e}")
            
    def add_node(self, node_id: str, data: Dict[str, Any], node_type: str = "general") -> bool:
        """Add a node to the knowledge graph"""
        if not self.connected:
            return False
            
        try:
            with self.driver.session() as session:
                query = """
                MERGE (n:KairosNode {node_id: $node_id})
                SET n.node_type = $node_type,
                    n.data = $data,
                    n.created_at = $timestamp,
                    n.updated_at = $timestamp
                RETURN n.node_id as created_id
                """
                
                result = session.run(query, {
                    "node_id": node_id,
                    "node_type": node_type,
                    "data": json.dumps(data),
                    "timestamp": datetime.now().isoformat()
                })
                
                if result.single():
                    self.logger.info(f"✅ Added Neo4j node: {node_id} (type: {node_type})")
                    
                    # Broadcast graph update via WebSocket
                    if self.websocket_manager:
                        asyncio.create_task(self._broadcast_graph_update({
                            "type": "node_added",
                            "node_id": node_id,
                            "node_type": node_type,
                            "data": data,
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to add node {node_id}: {e}")
            
        return False
        
    def add_edge(self, from_node: str, to_node: str, relationship: str, properties: Dict = None) -> bool:
        """Add a relationship between two nodes"""
        if not self.connected:
            return False
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (a:KairosNode {node_id: $from_node})
                MATCH (b:KairosNode {node_id: $to_node})
                CREATE (a)-[r:%s {properties: $properties, created_at: $timestamp}]->(b)
                RETURN r
                """ % relationship.upper().replace(' ', '_')
                
                result = session.run(query, {
                    "from_node": from_node,
                    "to_node": to_node,
                    "properties": json.dumps(properties or {}),
                    "timestamp": datetime.now().isoformat()
                })
                
                if result.single():
                    self.logger.info(f"✅ Added Neo4j edge: {from_node} --{relationship}--> {to_node}")
                    
                    # Broadcast graph update via WebSocket
                    if self.websocket_manager:
                        asyncio.create_task(self._broadcast_graph_update({
                            "type": "relationship_added",
                            "from_node": from_node,
                            "to_node": to_node,
                            "relationship": relationship,
                            "properties": properties or {},
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    return True
                    
        except Exception as e:
            self.logger.error(f"Failed to add edge {from_node} -> {to_node}: {e}")
            
        return False
        
    def add_context_memory(self, content: str, context_type: str = "general", metadata: Dict = None) -> str:
        """Add contextual memory with automatic ID generation"""
        if not self.connected:
            return None
            
        memory_id = hashlib.md5(f"{content}_{datetime.now().isoformat()}".encode()).hexdigest()[:12]
        
        try:
            with self.driver.session() as session:
                query = """
                CREATE (m:KairosMemory {
                    memory_id: $memory_id,
                    content: $content,
                    context_type: $context_type,
                    metadata: $metadata,
                    created_at: $timestamp
                })
                RETURN m.memory_id as created_id
                """
                
                result = session.run(query, {
                    "memory_id": memory_id,
                    "content": content,
                    "context_type": context_type,
                    "metadata": json.dumps(metadata or {}),
                    "timestamp": datetime.now().isoformat()
                })
                
                if result.single():
                    self.logger.info(f"✅ Added Neo4j context memory: {memory_id} (type: {context_type})")
                    
                    # Broadcast memory update via WebSocket
                    if self.websocket_manager:
                        asyncio.create_task(self._broadcast_graph_update({
                            "type": "memory_added",
                            "memory_id": memory_id,
                            "content": content[:100] + "..." if len(content) > 100 else content,
                            "context_type": context_type,
                            "metadata": metadata or {},
                            "timestamp": datetime.now().isoformat()
                        }))
                    
                    return memory_id
                    
        except Exception as e:
            self.logger.error(f"Failed to add context memory: {e}")
            
        return None
        
    def query_nodes(self, query: str, node_type: str = None, limit: int = 10) -> List[Dict]:
        """Query nodes using Cypher"""
        if not self.connected:
            return []
            
        try:
            with self.driver.session() as session:
                cypher_query = """
                MATCH (n:KairosNode)
                WHERE ($node_type IS NULL OR n.node_type = $node_type)
                AND (toLower(n.data) CONTAINS toLower($query) 
                     OR toLower(n.node_type) CONTAINS toLower($query))
                RETURN n.node_id as id, n.node_type as type, n.data as data, 
                       n.created_at as created_at
                ORDER BY n.created_at DESC
                LIMIT $limit
                """
                
                results = session.run(cypher_query, {
                    "query": query,
                    "node_type": node_type,
                    "limit": limit
                })
                
                nodes = []
                for record in results:
                    try:
                        data = json.loads(record["data"]) if record["data"] else {}
                    except:
                        data = {"raw": record["data"]}
                        
                    nodes.append({
                        "id": record["id"],
                        "type": record["type"],
                        "data": data,
                        "created_at": record["created_at"]
                    })
                    
                return nodes
                
        except Exception as e:
            self.logger.error(f"Node query failed: {e}")
            return []
            
    def query_context(self, query: str, context_type: str = None, limit: int = 5) -> List[Dict]:
        """Query context memories"""
        if not self.connected:
            return []
            
        try:
            with self.driver.session() as session:
                cypher_query = """
                MATCH (m:KairosMemory)
                WHERE ($context_type IS NULL OR m.context_type = $context_type)
                AND toLower(m.content) CONTAINS toLower($query)
                RETURN m.memory_id as id, m.content as content, 
                       m.context_type as context_type, m.metadata as metadata,
                       m.created_at as created_at
                ORDER BY m.created_at DESC
                LIMIT $limit
                """
                
                results = session.run(cypher_query, {
                    "query": query,
                    "context_type": context_type,
                    "limit": limit
                })
                
                memories = []
                for record in results:
                    try:
                        metadata = json.loads(record["metadata"]) if record["metadata"] else {}
                    except:
                        metadata = {}
                        
                    memories.append({
                        "id": record["id"],
                        "content": record["content"],
                        "context_type": record["context_type"],
                        "metadata": metadata,
                        "created_at": record["created_at"]
                    })
                    
                return memories
                
        except Exception as e:
            self.logger.error(f"Context query failed: {e}")
            return []
        
    def get_node_relationships(self, node_id: str) -> List[Dict]:
        """Get all relationships for a node using Cypher"""
        if not self.connected:
            return []
            
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n:KairosNode {node_id: $node_id})
                OPTIONAL MATCH (n)-[r1]->(other1:KairosNode)
                OPTIONAL MATCH (other2:KairosNode)-[r2]->(n)
                RETURN 
                    collect(DISTINCT {
                        direction: 'outgoing',
                        to: other1.node_id,
                        relationship: type(r1),
                        properties: r1.properties,
                        created_at: r1.created_at
                    }) as outgoing,
                    collect(DISTINCT {
                        direction: 'incoming', 
                        from: other2.node_id,
                        relationship: type(r2),
                        properties: r2.properties,
                        created_at: r2.created_at
                    }) as incoming
                """
                
                result = session.run(query, {"node_id": node_id})
                record = result.single()
                
                if record:
                    relationships = []
                    
                    # Add outgoing relationships
                    for rel in record["outgoing"]:
                        if rel["to"]:  # Filter out null relationships
                            relationships.append(rel)
                    
                    # Add incoming relationships  
                    for rel in record["incoming"]:
                        if rel["from"]:  # Filter out null relationships
                            relationships.append(rel)
                            
                    return relationships
                    
        except Exception as e:
            self.logger.error(f"Failed to get relationships for {node_id}: {e}")
            
        return []
        
    def get_stats(self) -> Dict[str, Any]:
        """Get Neo4j knowledge graph statistics"""
        if not self.connected:
            return {"connected": False, "error": "Not connected to Neo4j"}
            
        try:
            with self.driver.session() as session:
                # Count nodes and relationships
                node_count = session.run("MATCH (n:KairosNode) RETURN count(n) as count").single()["count"]
                memory_count = session.run("MATCH (m:KairosMemory) RETURN count(m) as count").single()["count"]
                relationship_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
                
                # Get node types distribution
                node_types_result = session.run("""
                    MATCH (n:KairosNode) 
                    RETURN n.node_type as type, count(*) as count 
                    ORDER BY count DESC
                """)
                node_types = {record["type"]: record["count"] for record in node_types_result}
                
                return {
                    "storage_type": "neo4j",
                    "connected": True,
                    "stats": {
                        "nodes_count": node_count,
                        "memories_count": memory_count,
                        "relationships_count": relationship_count,
                        "node_types": node_types
                    },
                    "connection_info": {
                        "uri": self.uri,
                        "username": self.username
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {"connected": False, "error": str(e)}
            
    async def _broadcast_graph_update(self, update_data: Dict[str, Any]):
        """Broadcast graph updates via WebSocket"""
        try:
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_topic("graph_updates", {
                    "event": "graph_update",
                    "data": update_data
                })
        except Exception as e:
            self.logger.error(f"Failed to broadcast graph update: {e}")
            
    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            self.connected = False
            self.logger.info("🔌 Neo4j connection closed")
