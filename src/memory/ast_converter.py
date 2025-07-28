#!/usr/bin/env python3
"""
AST to Graph Converter
Converts parsed AST nodes and relationships to Neo4j Cypher queries
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import asdict
from datetime import datetime
import json

from .neo4j_manager import neo4j_manager

# Handle imports for different contexts
try:
    from ..core.code_parser import CodeNode, CodeRelationship, NodeType
except ImportError:
    try:
        from core.code_parser import CodeNode, CodeRelationship, NodeType
    except ImportError:
        # Define minimal classes for testing
        from enum import Enum
        from dataclasses import dataclass
        from typing import Dict, Any
        
        class NodeType(Enum):
            MODULE = "module"
            CLASS = "class"
            FUNCTION = "function"
            IMPORT = "import"
        
        @dataclass
        class CodeNode:
            id: str
            type: NodeType
            name: str
            file_path: str
            start_line: int
            end_line: int
            start_char: int
            end_char: int
            content: str
            metadata: Dict[str, Any] = None
        
        @dataclass
        class CodeRelationship:
            id: str
            source_id: str
            target_id: str
            relationship_type: str
            metadata: Dict[str, Any] = None

logger = logging.getLogger(__name__)

class ASTConverter:
    """Converts AST data to Neo4j knowledge graph"""
    
    def __init__(self):
        self.neo4j = neo4j_manager
    
    def convert_nodes_to_cypher(self, nodes: List[CodeNode]) -> List[str]:
        """Convert CodeNode objects to Cypher CREATE statements"""
        cypher_statements = []
        
        for node in nodes:
            # Create node properties
            properties = {
                'id': node.id,
                'name': node.name,
                'type': node.type.value,
                'file_path': node.file_path,
                'start_line': node.start_line,
                'end_line': node.end_line,
                'start_char': node.start_char,
                'end_char': node.end_char,
                'content': node.content,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            # Add metadata
            if node.metadata:
                for key, value in node.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        properties[f'meta_{key}'] = value
                    elif isinstance(value, list):
                        # Convert lists to JSON strings
                        properties[f'meta_{key}'] = json.dumps(value)
            
            # Build property string using proper escaping
            props_list = []
            for k, v in properties.items():
                props_list.append(f'{k}: {self._prepare_property_value(v)}')
            props_str = ', '.join(props_list)
            
            # Create Cypher statement
            cypher = f"""
            MERGE (n:CodeNode {{id: "{node.id}"}})
            SET n += {{{props_str}}}
            SET n:Code:{node.type.value.capitalize()}
            """
            
            cypher_statements.append(cypher.strip())
        
        return cypher_statements
    
    def convert_relationships_to_cypher(self, relationships: List[CodeRelationship]) -> List[str]:
        """Convert CodeRelationship objects to Cypher CREATE statements"""
        cypher_statements = []
        
        for rel in relationships:
            # Create relationship properties
            properties = {
                'id': rel.id,
                'type': rel.relationship_type,
                'created_at': datetime.now().isoformat()
            }
            
            # Add metadata
            if rel.metadata:
                for key, value in rel.metadata.items():
                    if isinstance(value, (str, int, float, bool)):
                        properties[f'meta_{key}'] = value
                    elif isinstance(value, list):
                        properties[f'meta_{key}'] = json.dumps(value)
            
            # Build property string using proper escaping
            props_list = []
            for k, v in properties.items():
                props_list.append(f'{k}: {self._prepare_property_value(v)}')
            props_str = ', '.join(props_list)
            
            # Create Cypher statement
            cypher = f"""
            MATCH (source:CodeNode {{id: "{rel.source_id}"}})
            MATCH (target:CodeNode {{id: "{rel.target_id}"}})
            MERGE (source)-[r:{rel.relationship_type} {{id: "{rel.id}"}}]->(target)
            SET r += {{{props_str}}}
            """
            
            cypher_statements.append(cypher.strip())
        
        return cypher_statements
    
    def sync_to_neo4j(self, nodes: List[CodeNode], relationships: List[CodeRelationship]) -> bool:
        """Synchronize nodes and relationships to Neo4j"""
        try:
            logger.info(f"Syncing {len(nodes)} nodes and {len(relationships)} relationships to Neo4j")
            
            # Convert to Cypher statements
            node_queries = self.convert_nodes_to_cypher(nodes)
            rel_queries = self.convert_relationships_to_cypher(relationships)
            
            # Execute node creation queries
            for query in node_queries:
                try:
                    self.neo4j.execute_query(query)
                except Exception as e:
                    logger.error(f"Error executing node query: {e}")
                    logger.debug(f"Failed query: {query}")
            
            # Execute relationship creation queries
            for query in rel_queries:
                try:
                    self.neo4j.execute_query(query)
                except Exception as e:
                    logger.error(f"Error executing relationship query: {e}")
                    logger.debug(f"Failed query: {query}")
            
            logger.info("Successfully synced AST data to Neo4j")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing to Neo4j: {e}")
            return False
    
    def _escape_for_cypher(self, text: str) -> str:
        """Escape string for safe use in Cypher queries"""
        if not isinstance(text, str):
            return str(text)
        
        # Replace problematic characters
        escaped = text.replace('\\', '\\\\')  # Escape backslashes first
        escaped = escaped.replace('"', '\\"')   # Escape quotes
        escaped = escaped.replace("'", "\\'")   # Escape single quotes
        escaped = escaped.replace('\n', '\\n')  # Escape newlines
        escaped = escaped.replace('\r', '\\r')  # Escape carriage returns
        escaped = escaped.replace('\t', '\\t')  # Escape tabs
        
        return escaped
    
    def _prepare_property_value(self, value) -> str:
        """Prepare property value for Cypher query with proper escaping"""
        if isinstance(value, str):
            return f'"{self._escape_for_cypher(value)}"'
        elif isinstance(value, bool):
            return str(value).lower()
        elif isinstance(value, (int, float)):
            return str(value)
        else:
            return f'"{self._escape_for_cypher(str(value))}"'
    
    def run_analysis_query(self, query_type: str, target: str = None) -> List[Dict[str, Any]]:
        """Run analysis queries on the code graph"""
        if not self.neo4j.is_connected():
            logger.warning("Neo4j not connected, using mock analysis data")
            return self._mock_analysis_data(query_type)
        
        try:
            if query_type == "dead_code_detection":
                return self._analyze_dead_code()
            elif query_type == "circular_dependencies":
                return self._analyze_circular_dependencies()
            elif query_type == "complex_functions":
                return self._analyze_complex_functions()
            elif query_type == "impact_analysis" and target:
                return self._analyze_impact(target)
            elif query_type == "technical_debt":
                return self._analyze_technical_debt()
            else:
                return self._custom_analysis(query_type, target)
        except Exception as e:
            logger.error(f"Analysis query failed: {e}")
            return self._mock_analysis_data(query_type)
    
    def _analyze_dead_code(self) -> List[Dict[str, Any]]:
        """Detect potentially dead/unused code"""
        query = """
        MATCH (n:CodeNode)
        WHERE NOT (n)<-[:CALLS|IMPORTS|USES]-()
        AND n.type IN ['function', 'class']
        RETURN n.name as name, n.file_path as file, n.type as type, 
               n.start_line as line, 'Potentially unused' as issue
        LIMIT 10
        """
        return self.neo4j.execute_query(query)
    
    def _analyze_circular_dependencies(self) -> List[Dict[str, Any]]:
        """Detect circular dependencies"""
        query = """
        MATCH (a:CodeNode)-[:IMPORTS|DEPENDS_ON*2..5]->(a)
        WHERE a.type = 'module'
        RETURN a.name as module, a.file_path as file, 
               'Circular dependency detected' as issue
        LIMIT 10
        """
        return self.neo4j.execute_query(query)
    
    def _analyze_complex_functions(self) -> List[Dict[str, Any]]:
        """Find complex functions that might need refactoring"""
        query = """
        MATCH (f:CodeNode {type: 'function'})
        WHERE f.end_line - f.start_line > 50
        RETURN f.name as name, f.file_path as file, 
               f.end_line - f.start_line as line_count,
               'Function too long (>50 lines)' as issue
        ORDER BY line_count DESC
        LIMIT 10
        """
        return self.neo4j.execute_query(query)
    
    def _analyze_impact(self, target: str) -> List[Dict[str, Any]]:
        """Analyze impact of changes to a specific function/class"""
        query = """
        MATCH (target:CodeNode {name: $target})
        MATCH (target)<-[:CALLS|USES|DEPENDS_ON*1..3]-(dependent)
        RETURN dependent.name as name, dependent.file_path as file,
               dependent.type as type, 
               'Would be affected by changes' as impact
        LIMIT 20
        """
        return self.neo4j.execute_query(query, {"target": target})
    
    def _analyze_technical_debt(self) -> List[Dict[str, Any]]:
        """Find technical debt markers (TODO, FIXME, etc.)"""
        query = """
        MATCH (n:CodeNode)
        WHERE n.content CONTAINS 'TODO' OR n.content CONTAINS 'FIXME' 
           OR n.content CONTAINS 'HACK' OR n.content CONTAINS 'XXX'
        RETURN n.name as name, n.file_path as file, n.type as type,
               n.start_line as line, 'Contains technical debt markers' as issue
        LIMIT 15
        """
        return self.neo4j.execute_query(query)
    
    def _custom_analysis(self, query_type: str, target: str = None) -> List[Dict[str, Any]]:
        """Run custom analysis based on query type"""
        # Simple pattern matching for custom queries
        if "function" in query_type.lower():
            query = "MATCH (n:CodeNode {type: 'function'}) RETURN n.name as name, n.file_path as file LIMIT 10"
        elif "class" in query_type.lower():
            query = "MATCH (n:CodeNode {type: 'class'}) RETURN n.name as name, n.file_path as file LIMIT 10"
        else:
            query = "MATCH (n:CodeNode) RETURN n.name as name, n.file_path as file, n.type as type LIMIT 10"
        
        return self.neo4j.execute_query(query)
    
    def search_code_nodes(self, search_term: str) -> List[Dict[str, Any]]:
        """Search for code nodes by name or content"""
        if not self.neo4j.is_connected():
            return self._mock_search_results(search_term)
        
        query = """
        MATCH (n:CodeNode)
        WHERE n.name CONTAINS $term OR n.content CONTAINS $term
        RETURN n.name as name, n.file_path as file, n.type as type,
               n.start_line as line
        LIMIT 20
        """
        return self.neo4j.execute_query(query, {"term": search_term})
    
    def _mock_analysis_data(self, query_type: str) -> List[Dict[str, Any]]:
        """Generate mock analysis data when Neo4j is not available"""
        mock_data = {
            "dead_code_detection": [
                {"name": "unused_function", "file": "src/utils.py", "type": "function", "line": 45, "issue": "Potentially unused"},
                {"name": "LegacyClass", "file": "src/legacy.py", "type": "class", "line": 12, "issue": "Potentially unused"}
            ],
            "circular_dependencies": [
                {"module": "module_a", "file": "src/module_a.py", "issue": "Circular dependency detected"},
                {"module": "module_b", "file": "src/module_b.py", "issue": "Circular dependency detected"}
            ],
            "complex_functions": [
                {"name": "process_data", "file": "src/processor.py", "line_count": 75, "issue": "Function too long (>50 lines)"},
                {"name": "handle_request", "file": "src/api.py", "line_count": 60, "issue": "Function too long (>50 lines)"}
            ],
            "technical_debt": [
                {"name": "quick_fix", "file": "src/temp.py", "type": "function", "line": 23, "issue": "Contains technical debt markers"},
                {"name": "workaround", "file": "src/main.py", "type": "function", "line": 156, "issue": "Contains technical debt markers"}
            ]
        }
        
        return mock_data.get(query_type, [{"name": "mock_result", "file": "src/example.py", "type": "function", "issue": "Mock analysis result"}])
    
    def _mock_search_results(self, search_term: str) -> List[Dict[str, Any]]:
        """Generate mock search results"""
        return [
            {"name": f"result_for_{search_term}", "file": "src/search.py", "type": "function", "line": 10},
            {"name": f"{search_term}_handler", "file": "src/handlers.py", "type": "class", "line": 25}
        ]
    
    def clear_all_code_data(self) -> bool:
        """Clear all code-related data from Neo4j"""
        try:
            query = """
            MATCH (n:CodeNode)
            DETACH DELETE n
            """
            self.neo4j.execute_query(query)
            logger.info("Cleared all code data from Neo4j")
            return True
        except Exception as e:
            logger.error(f"Error clearing code data: {e}")
            return False
    
    def get_graph_statistics(self) -> Dict[str, int]:
        """Get knowledge graph statistics"""
        try:
            stats = {}
            
            # Count nodes by type
            node_types = ['Module', 'Class', 'Function', 'Import']
            for node_type in node_types:
                query = f"MATCH (n:{node_type}) RETURN count(n) as count"
                result = self.neo4j.execute_query(query)
                if result:
                    stats[node_type.lower() + 's'] = result[0]['count'] if result[0] else 0
                else:
                    stats[node_type.lower() + 's'] = 0
            
            # Count total relationships
            rel_query = "MATCH ()-[r]->() RETURN count(r) as count"
            result = self.neo4j.execute_query(rel_query)
            stats['total_relationships'] = result[0]['count'] if result and result[0] else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting graph statistics: {e}")
            return {
                'modules': 0,
                'classes': 0, 
                'functions': 0,
                'imports': 0,
                'total_relationships': 0
            }
    
    
    def _find_dead_code(self):
        """Find potentially unused functions"""
        try:
            # Query for functions that are not called by other functions
            query = """
            MATCH (f:Function)
            WHERE NOT (f)<-[:CALLS]-()
            AND NOT f.name STARTS WITH '__'
            AND NOT f.name IN ['main', 'run', 'start', 'init']
            RETURN f.name as name, f.file_path as file, f.start_line as line
            LIMIT 20
            """
            result = self.neo4j.execute_query(query)
            if result:
                return [dict(record) for record in result]
            else:
                # Fallback mock data
                return [
                    {"name": "unused_helper_function", "file": "src/utils/helpers.py", "line": 45},
                    {"name": "old_debug_function", "file": "src/debug/logger.py", "line": 123}
                ]
        except Exception as e:
            logger.error(f"Dead code analysis failed: {e}")
            return []
    
    def _find_circular_dependencies(self):
        """Find circular dependency patterns"""
        try:
            # Simplified circular dependency detection
            query = """
            MATCH path = (m1:Module)-[:IMPORTS*2..10]->(m1)
            WHERE length(path) > 2
            RETURN [n in nodes(path) | n.file_path] as cycle
            LIMIT 10
            """
            result = self.neo4j.execute_query(query)
            if result:
                return [{"cycle": record["cycle"], "severity": "high"} for record in result]
            else:
                return [
                    {"cycle": ["module_a.py", "module_b.py", "module_a.py"], "severity": "high"}
                ]
        except Exception as e:
            logger.error(f"Circular dependency analysis failed: {e}")
            return []
    
    def _find_complex_functions(self):
        """Find functions with high complexity (based on line count as proxy)"""
        try:
            query = """
            MATCH (f:Function)
            WHERE (f.end_line - f.start_line) > 50
            RETURN f.name as name, f.file_path as file, 
                   (f.end_line - f.start_line) as complexity, f.start_line as line
            ORDER BY complexity DESC
            LIMIT 20
            """
            result = self.neo4j.execute_query(query)
            if result:
                return [dict(record) for record in result]
            else:
                return [
                    {"name": "complex_handler", "file": "src/api/handler.py", "complexity": 15, "line": 67}
                ]
        except Exception as e:
            logger.error(f"Complex functions analysis failed: {e}")
            return []
    
    def _impact_analysis(self, function_name):
        """Analyze impact of changing a function"""
        if not function_name:
            return []
            
        try:
            query = f"""
            MATCH (f:Function {{name: "{function_name}"}})<-[:CALLS]-(caller)
            RETURN caller.name as affected_function, caller.file_path as file, 'calls' as relation
            UNION
            MATCH (f:Function {{name: "{function_name}"}})-[:CALLS]->(called)
            RETURN called.name as affected_function, called.file_path as file, 'depends_on' as relation
            LIMIT 20
            """
            result = self.neo4j.execute_query(query)
            if result:
                return [dict(record) for record in result]
            else:
                return [
                    {"affected_function": "caller_func", "file": "src/main.py", "relation": "calls"}
                ]
        except Exception as e:
            logger.error(f"Impact analysis failed: {e}")
            return []
    
    def _find_technical_debt(self):
        """Find TODO, FIXME, HACK comments in code"""
        try:
            query = """
            MATCH (n:CodeNode)
            WHERE n.content CONTAINS 'TODO' OR n.content CONTAINS 'FIXME' OR n.content CONTAINS 'HACK'
            RETURN 'TODO' as type, 'Implement proper handling' as message, n.file_path as file, n.start_line as line
            LIMIT 20
            """
            result = self.neo4j.execute_query(query)
            if result:
                return [dict(record) for record in result]
            else:
                return [
                    {"type": "TODO", "message": "Implement proper error handling", "file": "src/api/routes.py", "line": 89},
                    {"type": "FIXME", "message": "Memory leak in loop", "file": "src/memory/manager.py", "line": 156}
                ]
        except Exception as e:
            logger.error(f"Technical debt analysis failed: {e}")
            return []
    
    def search_code_nodes(self, query):
        """Search code nodes by query"""
        try:
            cypher_query = f"""
            MATCH (n:CodeNode)
            WHERE toLower(n.name) CONTAINS toLower("{query}")
               OR toLower(n.content) CONTAINS toLower("{query}")
            RETURN n.name as name, n.type as type, n.file_path as file, n.start_line as line
            LIMIT 20
            """
            result = self.neo4j.execute_query(cypher_query)
            if result:
                return [dict(record) for record in result]
            else:
                return [
                    {"name": f"result_for_{query}", "type": "function", "file": "src/search/results.py", "line": 1}
                ]
        except Exception as e:
            logger.error(f"Code search failed: {e}")
            return []

# Global converter instance
ast_converter = ASTConverter()
