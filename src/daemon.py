"""
Kairos Daemon Service
Manages the lifecycle of the Kairos system as a daemon service.
"""

import os
import sys
import signal
import logging
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import psutil
import json

# Import core modules with error handling
try:
    from main import app
    from config_loader import config
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class KairosDaemon:
    """Daemon service for Kairos"""
    
    def __init__(self, pid_file: str = ".kairos.pid", log_file: str = "kairos.log"):
        self.pid_file = Path(pid_file)
        self.log_file = Path(log_file)
        self.logger = self._setup_logging()
        self.running = False
        self.start_time = None
        self.stats = {
            "start_time": None,
            "uptime": 0,
            "requests_handled": 0,
            "memory_usage": 0,
            "cpu_usage": 0
        }
        
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        if hasattr(signal, 'SIGHUP'):  # Unix only
            signal.signal(signal.SIGHUP, self._signal_handler)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for daemon"""
        logger = logging.getLogger('kairos_daemon')
        logger.setLevel(logging.INFO)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        return logger
    
    def _signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}")
        
        if signum == signal.SIGTERM or signum == signal.SIGINT:
            self.logger.info("Shutdown signal received")
            self.stop()
        elif hasattr(signal, 'SIGHUP') and signum == signal.SIGHUP:
            self.logger.info("Reload signal received")
            self.reload_config()
    
    def _write_pid(self) -> bool:
        """Write PID to file"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            return True
        except Exception as e:
            self.logger.error(f"Failed to write PID file: {e}")
            return False
    
    def _remove_pid(self):
        """Remove PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
        except Exception as e:
            self.logger.error(f"Failed to remove PID file: {e}")
    
    def _update_stats(self):
        """Update daemon statistics"""
        try:
            process = psutil.Process()
            self.stats.update({
                "uptime": time.time() - self.start_time if self.start_time else 0,
                "memory_usage": process.memory_info().rss / 1024 / 1024,  # MB
                "cpu_usage": process.cpu_percent()
            })
        except Exception as e:
            self.logger.error(f"Failed to update stats: {e}")
    
    def _stats_monitor(self):
        """Background stats monitoring"""
        while self.running:
            try:
                self._update_stats()
                time.sleep(30)  # Update every 30 seconds
            except Exception as e:
                self.logger.error(f"Stats monitor error: {e}")
                time.sleep(60)
    
    def get_status(self) -> dict:
        """Get daemon status"""
        self._update_stats()
        return {
            "status": "running" if self.running else "stopped",
            "pid": os.getpid(),
            "start_time": self.stats["start_time"],
            "uptime_seconds": self.stats["uptime"],
            "memory_mb": self.stats["memory_usage"],
            "cpu_percent": self.stats["cpu_usage"],
            "log_file": str(self.log_file),
            "pid_file": str(self.pid_file)
        }
    
    def reload_config(self):
        """Reload configuration"""
        try:
            self.logger.info("Reloading configuration...")
            config.reload()
            self.logger.info("Configuration reloaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to reload configuration: {e}")
    
    async def _run_server(self):
        """Run the FastAPI server and MCP server"""
        import uvicorn
        
        # Get configuration
        host = config.get('daemon.host', '0.0.0.0')
        port = config.get('daemon.port', 8000)
        workers = config.get('daemon.workers', 1)  # Use 1 for daemon mode
        
        self.logger.info(f"Starting server on {host}:{port}")
        
        # Start MCP server in background
        await self._start_mcp_server()
        
        # Start Supervisor Agent
        await self._start_supervisor_agent()
        
        # Start Code Graph File Watcher
        await self._start_code_graph_watcher()
        
        # Configure uvicorn
        server_config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="info",
            access_log=True
        )
        
        server = uvicorn.Server(server_config)
        await server.serve()
    
    async def _start_mcp_server(self):
        """Start MCP server as background service"""
        try:
            self.logger.info("🚀 Starting Kairos MCP Server...")
            
            # Import MCP server
            from src.mcp.kairos_mcp_final import KairosMCPServer
            
            # Create MCP server instance
            self.mcp_server = KairosMCPServer()
            
            # Start MCP server in background task
            asyncio.create_task(self._run_mcp_server())
            
            self.logger.info("✅ Kairos MCP Server started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start MCP server: {e}")
    
    async def _run_mcp_server(self):
        """Run MCP server loop"""
        try:
            while self.running:
                # MCP server listens on stdin/stdout
                # This is handled by the MCP protocol implementation
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"MCP server error: {e}")
    
    async def _start_supervisor_agent(self):
        """Start supervisor agent"""
        try:
            self.logger.info("🧠 Starting Supervisor Agent...")
            
            # Import supervisor agent
            from agents.enhanced_supervisor import EnhancedSupervisorAgent
            
            # Create supervisor instance
            self.supervisor = EnhancedSupervisorAgent()
            
            # Start supervisor in background task
            asyncio.create_task(self._run_supervisor_agent())
            
            self.logger.info("✅ Supervisor Agent started successfully")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Supervisor Agent: {e}")
    
    async def _start_code_graph_watcher(self):
        """Start file system watcher for automatic code graph updates"""
        try:
            self.logger.info("🔍 Starting Code Graph File Watcher...")
            
            # Import required modules
            from monitoring.project_watcher import ProjectWatcher
            from core.code_parser import code_parser
            from memory.ast_converter import ast_converter
            import os
            
            # Get current working directory as project path
            project_path = os.getcwd()
            
            # Create analysis callback for file changes
            async def code_analysis_callback(change_event):
                """Callback to handle code file changes"""
                try:
                    if change_event.is_code_file:
                        self.logger.info(f"🔄 Updating code graph for: {change_event.file_path}")
                        
                        if change_event.event_type == 'deleted':
                            # Remove nodes for deleted file
                            ast_converter.delete_file_nodes(change_event.file_path)
                            self.logger.info(f"🗑️ Removed nodes for deleted file: {change_event.file_path}")
                        else:
                            # Parse and update nodes for created/modified files
                            nodes, relationships = code_parser.parse_file(change_event.file_path)
                            
                            if nodes or relationships:
                                # First remove old nodes for this file
                                ast_converter.delete_file_nodes(change_event.file_path)
                                
                                # Then add new nodes
                                success = ast_converter.sync_to_neo4j(nodes, relationships)
                                
                                if success:
                                    self.logger.info(f"✅ Updated {len(nodes)} nodes, {len(relationships)} relationships for: {change_event.file_path}")
                                else:
                                    self.logger.error(f"❌ Failed to update code graph for: {change_event.file_path}")
                        
                except Exception as e:
                    self.logger.error(f"❌ Error in code analysis callback: {e}")
            
            # Create and start project watcher
            self.code_watcher = ProjectWatcher(project_path, code_analysis_callback)
            self.code_watcher.start()
            
            self.logger.info(f"✅ Code Graph File Watcher started for: {project_path}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Code Graph File Watcher: {e}")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to start Supervisor Agent: {e}")
    
    def start(self, detach: bool = True):
        """Start the daemon"""
        try:
            # Check if already running
            if self.pid_file.exists():
                with open(self.pid_file) as f:
                    old_pid = int(f.read().strip())
                
                if psutil.pid_exists(old_pid):
                    self.logger.error(f"Daemon already running with PID {old_pid}")
                    return False
                else:
                    self.logger.info(f"Removing stale PID file (PID {old_pid} not running)")
                    self._remove_pid()
            
            # Detach from terminal if requested
            if detach:
                self._daemonize()
            
            # Write PID file
            if not self._write_pid():
                return False
            
            # Initialize
            self.running = True
            self.start_time = time.time()
            self.stats["start_time"] = datetime.now().isoformat()
            
            self.logger.info(f"Kairos daemon started (PID: {os.getpid()})")
            
            # Start stats monitor thread
            stats_thread = threading.Thread(target=self._stats_monitor, daemon=True)
            stats_thread.start()
            
            # Start the main server
            asyncio.run(self._run_server())
            
        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            self._remove_pid()
            return False
        
        return True
    
    def _daemonize(self):
        """Daemonize the process (cross-platform)"""
        # On Windows, we don't use fork, just run in background
        if os.name == 'nt':  # Windows
            self.logger.info("Running in Windows mode (no fork)")
            return
        
        # Unix-style daemonization
        try:
            # First fork
            if os.fork() > 0:
                os._exit(0)
        except (OSError, AttributeError) as e:
            self.logger.error(f"First fork failed: {e}")
            sys.exit(1)
        
        # Decouple from parent environment
        os.chdir("/")
        os.setsid()
        os.umask(0)
        
        # Second fork
        try:
            if os.fork() > 0:
                os._exit(0)
        except OSError as e:
            self.logger.error(f"Second fork failed: {e}")
            sys.exit(1)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Redirect to log file or /dev/null
        si = open('/dev/null', 'r')
        so = open('/dev/null', 'a+')
        se = open('/dev/null', 'a+')
        
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
    
    def stop(self):
        """Stop the daemon"""
        self.logger.info("Stopping Kairos daemon...")
        self.running = False
        
        try:
            # Additional cleanup can be added here
            self._remove_pid()
            self.logger.info("Daemon stopped successfully")
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
        
        sys.exit(0)
    
    def is_running(self) -> bool:
        """Check if daemon is running"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file) as f:
                pid = int(f.read().strip())
            return psutil.pid_exists(pid)
        except (ValueError, FileNotFoundError):
            return False

def run_daemon(detach: bool = True):
    """Run Kairos as a daemon service"""
    # Load configuration
    config.load()
    
    # Create and start daemon
    daemon = KairosDaemon()
    daemon.start(detach=detach)

def main():
    """Main entry point for daemon"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Kairos Daemon Service')
    parser.add_argument('--no-detach', action='store_true',
                       help='Do not detach from terminal (foreground mode)')
    parser.add_argument('--config', '-c', type=str,
                       help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Load configuration
    if args.config:
        config.load(args.config)
    else:
        config.load()
    
    # Run daemon
    run_daemon(detach=not args.no_detach)


if __name__ == "__main__":
    main()
