import logging
import subprocess
import shlex
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from .base_agent import BaseAgent

# Import MCP for context management
try:
    from ..mcp.model_context_protocol import MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class ExecutionAgent(BaseAgent):
    """Agent responsible for executing tasks and commands provided in the project"""
    
    def __init__(self, mcp_context: Optional['MCPContext'] = None):
        super().__init__(name="ExecutionAgent", mcp_context)
        self.logger = logging.getLogger(__name__)
        
        # Allowed file operations for security
        self.allowed_extensions = {
            '.py', '.js', '.ts', '.html', '.css', '.json', '.md', '.txt', 
            '.yml', '.yaml', '.toml', '.sh', '.bat', '.sql', '.xml'
        }
        
        # Safe directories for file operations
        self.safe_directories = {
            'src/', 'docs/', 'scripts/', 'tests/', 'frontend/', 
            'configs/', 'examples/', 'temp/', 'output/'
        }
        
    def execute(self, command: str) -> Dict[str, str]:
        """Execute a command and return the result"""
        self.logger.info(f"Executing command: {command}")
        print(f"⚙️ Executing command: {command}")
        
        try:
            result = subprocess.run(shlex.split(command), capture_output=True, text=True, check=True)
            self.logger.info(f"Execution successful: {result.stdout[:100]}")
            return {
                "status": "success",
                "output": result.stdout,
                "executed_at": datetime.now().isoformat()
            }
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Execution failed: {e.stderr}")
            return {
                "status": "failure",
                "error": e.stderr,
                "executed_at": datetime.now().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Unexpected error during execution: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "executed_at": datetime.now().isoformat()
            }
            
    def create_file(self, file_path: str, content: str, overwrite: bool = False) -> Dict[str, Any]:
        """Create a new file with the given content"""
        self.logger.info(f"Creating file: {file_path}")
        
        try:
            # Security check
            if not self._is_safe_path(file_path):
                return {
                    "status": "error",
                    "error": f"File path '{file_path}' is not in allowed directories",
                    "created_at": datetime.now().isoformat()
                }
            
            path = Path(file_path)
            
            # Check extension
            if path.suffix.lower() not in self.allowed_extensions:
                return {
                    "status": "error",
                    "error": f"File extension '{path.suffix}' is not allowed",
                    "created_at": datetime.now().isoformat()
                }
            
            # Check if file exists
            if path.exists() and not overwrite:
                return {
                    "status": "error",
                    "error": f"File '{file_path}' already exists. Use overwrite=True to replace.",
                    "created_at": datetime.now().isoformat()
                }
            
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.local_context['last_file_created'] = {
                    'path': file_path,
                    'size': len(content),
                    'timestamp': datetime.now().isoformat()
                }
            
            self.logger.info(f"✅ File created successfully: {file_path}")
            return {
                "status": "success",
                "file_path": file_path,
                "size_bytes": len(content.encode('utf-8')),
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create file {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e),
                "created_at": datetime.now().isoformat()
            }
    
    def read_file(self, file_path: str) -> Dict[str, Any]:
        """Read the content of a file"""
        self.logger.info(f"Reading file: {file_path}")
        
        try:
            # Security check
            if not self._is_safe_path(file_path):
                return {
                    "status": "error",
                    "error": f"File path '{file_path}' is not in allowed directories"
                }
            
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "error": f"File '{file_path}' does not exist"
                }
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.local_context['last_file_read'] = {
                    'path': file_path,
                    'size': len(content),
                    'timestamp': datetime.now().isoformat()
                }
            
            return {
                "status": "success",
                "file_path": file_path,
                "content": content,
                "size_bytes": len(content.encode('utf-8')),
                "read_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def update_file(self, file_path: str, content: str, backup: bool = True) -> Dict[str, Any]:
        """Update an existing file with new content"""
        self.logger.info(f"Updating file: {file_path}")
        
        try:
            # Security check
            if not self._is_safe_path(file_path):
                return {
                    "status": "error",
                    "error": f"File path '{file_path}' is not in allowed directories"
                }
            
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "error": f"File '{file_path}' does not exist. Use create_file instead."
                }
            
            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = f"{file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
            
            # Write new content
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.local_context['last_file_updated'] = {
                    'path': file_path,
                    'backup_path': backup_path,
                    'size': len(content),
                    'timestamp': datetime.now().isoformat()
                }
            
            self.logger.info(f"✅ File updated successfully: {file_path}")
            return {
                "status": "success",
                "file_path": file_path,
                "backup_path": backup_path,
                "size_bytes": len(content.encode('utf-8')),
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to update file {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def delete_file(self, file_path: str, backup: bool = True) -> Dict[str, Any]:
        """Delete a file (with optional backup)"""
        self.logger.info(f"Deleting file: {file_path}")
        
        try:
            # Security check
            if not self._is_safe_path(file_path):
                return {
                    "status": "error",
                    "error": f"File path '{file_path}' is not in allowed directories"
                }
            
            path = Path(file_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "error": f"File '{file_path}' does not exist"
                }
            
            backup_path = None
            if backup:
                backup_path = f"{file_path}.deleted.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                with open(backup_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # Delete the file
            path.unlink()
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.local_context['last_file_deleted'] = {
                    'path': file_path,
                    'backup_path': backup_path,
                    'timestamp': datetime.now().isoformat()
                }
            
            self.logger.info(f"✅ File deleted successfully: {file_path}")
            return {
                "status": "success",
                "file_path": file_path,
                "backup_path": backup_path,
                "deleted_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def list_directory(self, directory_path: str = ".") -> Dict[str, Any]:
        """List contents of a directory"""
        self.logger.info(f"Listing directory: {directory_path}")
        
        try:
            # Security check
            if not self._is_safe_path(directory_path):
                return {
                    "status": "error",
                    "error": f"Directory path '{directory_path}' is not in allowed directories"
                }
            
            path = Path(directory_path)
            
            if not path.exists():
                return {
                    "status": "error",
                    "error": f"Directory '{directory_path}' does not exist"
                }
            
            if not path.is_dir():
                return {
                    "status": "error",
                    "error": f"'{directory_path}' is not a directory"
                }
            
            contents = []
            for item in path.iterdir():
                item_info = {
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
                contents.append(item_info)
            
            # Sort by name
            contents.sort(key=lambda x: x["name"])
            
            return {
                "status": "success",
                "directory_path": directory_path,
                "contents": contents,
                "total_items": len(contents),
                "listed_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to list directory {directory_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def create_directory(self, directory_path: str) -> Dict[str, Any]:
        """Create a new directory"""
        self.logger.info(f"Creating directory: {directory_path}")
        
        try:
            # Security check
            if not self._is_safe_path(directory_path):
                return {
                    "status": "error",
                    "error": f"Directory path '{directory_path}' is not in allowed directories"
                }
            
            path = Path(directory_path)
            
            if path.exists():
                return {
                    "status": "error",
                    "error": f"Directory '{directory_path}' already exists"
                }
            
            # Create directory with parents
            path.mkdir(parents=True, exist_ok=False)
            
            # Update MCP context if available
            if self.mcp_context:
                self.mcp_context.local_context['last_directory_created'] = {
                    'path': directory_path,
                    'timestamp': datetime.now().isoformat()
                }
            
            self.logger.info(f"✅ Directory created successfully: {directory_path}")
            return {
                "status": "success",
                "directory_path": directory_path,
                "created_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create directory {directory_path}: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _is_safe_path(self, path: str) -> bool:
        """Check if the path is in allowed directories"""
        normalized_path = os.path.normpath(path).replace('\\', '/')
        
        # Don't allow absolute paths outside project
        if os.path.isabs(normalized_path) and not normalized_path.startswith(os.getcwd().replace('\\', '/')):
            return False
        
        # Check against safe directories
        for safe_dir in self.safe_directories:
            if normalized_path.startswith(safe_dir) or normalized_path.startswith('./' + safe_dir):
                return True
        
        # Allow current directory files with safe extensions
        if '/' not in normalized_path.lstrip('./'):
            return True
        
        return False
    
    def execute_with_context(self, command: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute command with additional context from MCP"""
        self.logger.info(f"Executing command with context: {command}")
        
        # Merge MCP context if available
        full_context = {}
        if self.mcp_context:
            full_context.update(self.mcp_context.local_context)
        if context:
            full_context.update(context)
        
        # Execute the command
        result = self.execute(command)
        
        # Add context information to result
        result['context_used'] = full_context
        result['mcp_context_available'] = self.mcp_context is not None
        
        # Update MCP context with execution result
        if self.mcp_context:
            self.mcp_context.local_context['last_execution'] = {
                'command': command,
                'result': result['status'],
                'timestamp': datetime.now().isoformat()
            }
        
        return result
    
    def get_status(self):
        return {
            "name": self.name,
            "status": self.status,
            "last_activity": datetime.now().isoformat(),
            "allowed_extensions": list(self.allowed_extensions),
            "safe_directories": list(self.safe_directories),
            "mcp_context_available": self.mcp_context is not None
        }
