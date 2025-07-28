#!/usr/bin/env python3
"""
Code Parser Module
Uses Tree-sitter to parse code files and extract Abstract Syntax Trees (AST)
"""

import os
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import json
import ast

logger = logging.getLogger(__name__)

class NodeType(Enum):
    """AST node types for code analysis"""
    MODULE = "module"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    IMPORT = "import"
    CALL = "call"
    COMMENT = "comment"

@dataclass
class CodeNode:
    """Represents a node in the code AST"""
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
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class CodeRelationship:
    """Represents a relationship between code nodes"""
    id: str
    source_id: str
    target_id: str
    relationship_type: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class CodeParser:
    """Main code parser using Tree-sitter"""
    
    def __init__(self):
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.json': 'json',
            '.md': 'markdown'
        }
        self.parsers_cache = {}
        self._setup_tree_sitter()
    
    def _setup_tree_sitter(self):
        """Setup Tree-sitter parsers for supported languages"""
        try:
            # For now, we'll implement a simpler AST parser without Tree-sitter
            # This can be upgraded to use Tree-sitter later
            logger.info("Code parser initialized (simple mode)")
        except ImportError:
            logger.warning("Tree-sitter not available, using simple parser")
    
    def parse_file(self, file_path: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse a single file and extract nodes and relationships"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return [], []
            
            extension = file_path.suffix.lower()
            if extension not in self.supported_languages:
                logger.debug(f"Unsupported file type: {extension}")
                return [], []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse based on file type
            if extension == '.py':
                return self._parse_python_file(str(file_path), content)
            elif extension in ['.js', '.jsx']:
                return self._parse_javascript_file(str(file_path), content)
            elif extension in ['.ts', '.tsx']:
                return self._parse_typescript_file(str(file_path), content)
            elif extension == '.json':
                return self._parse_json_file(str(file_path), content)
            elif extension == '.md':
                return self._parse_markdown_file(str(file_path), content)
            else:
                return [], []
                
        except Exception as e:
            logger.error(f"Error parsing file {file_path}: {e}")
            return [], []
    
    def _parse_python_file(self, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse Python file using AST"""
        import ast
        
        nodes = []
        relationships = []
        
        try:
            tree = ast.parse(content)
            
            # Create module node
            module_id = self._generate_id(file_path, "module", Path(file_path).stem)
            module_node = CodeNode(
                id=module_id,
                type=NodeType.MODULE,
                name=Path(file_path).stem,
                file_path=file_path,
                start_line=1,
                end_line=len(content.split('\n')),
                start_char=0,
                end_char=len(content),
                content=content[:200] + "..." if len(content) > 200 else content,
                metadata={
                    "language": "python",
                    "size": len(content),
                    "lines": len(content.split('\n'))
                }
            )
            nodes.append(module_node)
            
            # Parse AST nodes
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_node = self._create_function_node(node, file_path, content)
                    nodes.append(func_node)
                    
                    # Create relationship between module and function
                    rel_id = self._generate_relationship_id(module_id, func_node.id, "HAS_FUNCTION")
                    relationship = CodeRelationship(
                        id=rel_id,
                        source_id=module_id,
                        target_id=func_node.id,
                        relationship_type="HAS_FUNCTION"
                    )
                    relationships.append(relationship)
                
                elif isinstance(node, ast.ClassDef):
                    class_node = self._create_class_node(node, file_path, content)
                    nodes.append(class_node)
                    
                    # Create relationship between module and class
                    rel_id = self._generate_relationship_id(module_id, class_node.id, "HAS_CLASS")
                    relationship = CodeRelationship(
                        id=rel_id,
                        source_id=module_id,
                        target_id=class_node.id,
                        relationship_type="HAS_CLASS"
                    )
                    relationships.append(relationship)
                
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    import_nodes, import_rels = self._create_import_nodes(node, file_path, content, module_id)
                    nodes.extend(import_nodes)
                    relationships.extend(import_rels)
            
        except SyntaxError as e:
            logger.error(f"Python syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error parsing Python file {file_path}: {e}")
        
        return nodes, relationships
    
    def _create_function_node(self, node: 'ast.FunctionDef', file_path: str, content: str) -> CodeNode:
        """Create a CodeNode for a Python function"""
        import ast
        lines = content.split('\n')
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Extract function signature
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"
        
        # Extract docstring if available
        docstring = ""
        if (node.body and isinstance(node.body[0], ast.Expr) 
            and isinstance(node.body[0].value, ast.Constant) 
            and isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        func_id = self._generate_id(file_path, "function", node.name)
        
        return CodeNode(
            id=func_id,
            type=NodeType.FUNCTION,
            name=node.name,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            start_char=0,  # Would need column info from Tree-sitter
            end_char=0,
            content=signature,
            metadata={
                "signature": signature,
                "args": args,
                "docstring": docstring,
                "decorators": [d.id for d in node.decorator_list if hasattr(d, 'id')],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "complexity": self._calculate_complexity(node)
            }
        )
    
    def _create_class_node(self, node: 'ast.ClassDef', file_path: str, content: str) -> CodeNode:
        """Create a CodeNode for a Python class"""
        lines = content.split('\n')
        start_line = node.lineno
        end_line = node.end_lineno or start_line
        
        # Extract base classes
        bases = []
        for base in node.bases:
            if hasattr(base, 'id'):
                bases.append(base.id)
            elif hasattr(base, 'attr'):
                bases.append(base.attr)
        
        # Extract docstring
        docstring = ""
        if (node.body and isinstance(node.body[0], ast.Expr) 
            and isinstance(node.body[0].value, ast.Constant) 
            and isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        class_id = self._generate_id(file_path, "class", node.name)
        
        return CodeNode(
            id=class_id,
            type=NodeType.CLASS,
            name=node.name,
            file_path=file_path,
            start_line=start_line,
            end_line=end_line,
            start_char=0,
            end_char=0,
            content=f"class {node.name}",
            metadata={
                "bases": bases,
                "docstring": docstring,
                "decorators": [d.id for d in node.decorator_list if hasattr(d, 'id')],
                "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            }
        )
    
    def _create_import_nodes(self, node: 'ast.stmt', file_path: str, content: str, module_id: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Create nodes and relationships for import statements"""
        import ast
        
        nodes = []
        relationships = []
        
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_id = self._generate_id(file_path, "import", alias.name)
                import_node = CodeNode(
                    id=import_id,
                    type=NodeType.IMPORT,
                    name=alias.name,
                    file_path=file_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    start_char=0,
                    end_char=0,
                    content=f"import {alias.name}",
                    metadata={
                        "alias": alias.asname,
                        "module": alias.name
                    }
                )
                nodes.append(import_node)
                
                # Create IMPORTS relationship
                rel_id = self._generate_relationship_id(module_id, import_id, "IMPORTS")
                relationship = CodeRelationship(
                    id=rel_id,
                    source_id=module_id,
                    target_id=import_id,
                    relationship_type="IMPORTS"
                )
                relationships.append(relationship)
        
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module or ""
            for alias in node.names:
                import_id = self._generate_id(file_path, "import", f"{module_name}.{alias.name}")
                import_node = CodeNode(
                    id=import_id,
                    type=NodeType.IMPORT,
                    name=alias.name,
                    file_path=file_path,
                    start_line=node.lineno,
                    end_line=node.lineno,
                    start_char=0,
                    end_char=0,
                    content=f"from {module_name} import {alias.name}",
                    metadata={
                        "alias": alias.asname,
                        "module": module_name,
                        "from_import": True
                    }
                )
                nodes.append(import_node)
                
                # Create IMPORTS relationship
                rel_id = self._generate_relationship_id(module_id, import_id, "IMPORTS")
                relationship = CodeRelationship(
                    id=rel_id,
                    source_id=module_id,
                    target_id=import_id,
                    relationship_type="IMPORTS"
                )
                relationships.append(relationship)
        
        return nodes, relationships
    
    def _parse_javascript_file(self, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse JavaScript file (simplified)"""
        # TODO: Implement JavaScript parsing
        nodes = []
        relationships = []
        
        # Create basic module node for now
        module_id = self._generate_id(file_path, "module", Path(file_path).stem)
        module_node = CodeNode(
            id=module_id,
            type=NodeType.MODULE,
            name=Path(file_path).stem,
            file_path=file_path,
            start_line=1,
            end_line=len(content.split('\n')),
            start_char=0,
            end_char=len(content),
            content=content[:200] + "..." if len(content) > 200 else content,
            metadata={
                "language": "javascript",
                "size": len(content),
                "lines": len(content.split('\n'))
            }
        )
        nodes.append(module_node)
        
        return nodes, relationships
    
    def _parse_typescript_file(self, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse TypeScript file (simplified)"""
        # TODO: Implement TypeScript parsing
        return self._parse_javascript_file(file_path, content)
    
    def _parse_json_file(self, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse JSON file"""
        nodes = []
        
        try:
            data = json.loads(content)
            
            module_id = self._generate_id(file_path, "module", Path(file_path).stem)
            module_node = CodeNode(
                id=module_id,
                type=NodeType.MODULE,
                name=Path(file_path).stem,
                file_path=file_path,
                start_line=1,
                end_line=len(content.split('\n')),
                start_char=0,
                end_char=len(content),
                content=json.dumps(data, indent=2)[:200] + "..." if len(content) > 200 else json.dumps(data, indent=2),
                metadata={
                    "language": "json",
                    "size": len(content),
                    "keys": list(data.keys()) if isinstance(data, dict) else [],
                    "type": type(data).__name__
                }
            )
            nodes.append(module_node)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in {file_path}: {e}")
        
        return nodes, []
    
    def _parse_markdown_file(self, file_path: str, content: str) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse Markdown file"""
        nodes = []
        
        # Extract headers
        lines = content.split('\n')
        headers = []
        
        for i, line in enumerate(lines, 1):
            if line.startswith('#'):
                level = len(line) - len(line.lstrip('#'))
                title = line.lstrip('#').strip()
                headers.append({
                    'level': level,
                    'title': title,
                    'line': i
                })
        
        module_id = self._generate_id(file_path, "module", Path(file_path).stem)
        module_node = CodeNode(
            id=module_id,
            type=NodeType.MODULE,
            name=Path(file_path).stem,
            file_path=file_path,
            start_line=1,
            end_line=len(lines),
            start_char=0,
            end_char=len(content),
            content=content[:200] + "..." if len(content) > 200 else content,
            metadata={
                "language": "markdown",
                "size": len(content),
                "lines": len(lines),
                "headers": headers
            }
        )
        nodes.append(module_node)
        
        return nodes, []
    
    def _calculate_complexity(self, node: 'ast.AST') -> int:
        """Calculate cyclomatic complexity of a function"""
        import ast
        
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _generate_id(self, file_path: str, node_type: str, name: str) -> str:
        """Generate unique ID for a code node"""
        content = f"{file_path}:{node_type}:{name}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def _generate_relationship_id(self, source_id: str, target_id: str, rel_type: str) -> str:
        """Generate unique ID for a relationship"""
        content = f"{source_id}:{target_id}:{rel_type}"
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def parse_directory(self, directory_path: str, exclude_patterns: List[str] = None) -> Tuple[List[CodeNode], List[CodeRelationship]]:
        """Parse all supported files in a directory"""
        if exclude_patterns is None:
            exclude_patterns = [
                '__pycache__',
                'node_modules',
                '.git',
                '.venv',
                '.env',
                'dist',
                'build'
            ]
        
        all_nodes = []
        all_relationships = []
        
        directory_path = Path(directory_path)
        
        # Walk through directory
        for file_path in directory_path.rglob('*'):
            if file_path.is_file():
                # Check if file should be excluded
                should_exclude = False
                file_str = str(file_path)
                for pattern in exclude_patterns:
                    if pattern in file_str:
                        should_exclude = True
                        break
                
                if not should_exclude:
                    nodes, relationships = self.parse_file(str(file_path))
                    all_nodes.extend(nodes)
                    all_relationships.extend(relationships)
        
        logger.info(f"Parsed {len(all_nodes)} nodes and {len(all_relationships)} relationships from {directory_path}")
        
        return all_nodes, all_relationships

# Global parser instance
code_parser = CodeParser()
