"""
🔍 Real-time Project Watcher
Monitors file changes and triggers intelligent analysis

Features:
- Real-time file system monitoring
- Smart filtering (only relevant files)
- Batch change processing
- Analysis trigger system
"""

import asyncio
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Callable
from dataclasses import dataclass
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import json
import logging
from datetime import datetime

@dataclass
class ChangeEvent:
    """Represents a file change event"""
    file_path: str
    event_type: str  # created, modified, deleted, moved
    timestamp: datetime
    file_extension: str
    file_size: Optional[int] = None
    is_code_file: bool = False

class SmartFileHandler(FileSystemEventHandler):
    """Intelligent file system event handler"""
    
    # Relevant file extensions for analysis
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.cs',
        '.go', '.rs', '.php', '.rb', '.swift', '.kt', '.scala', '.r',
        '.sql', '.html', '.css', '.scss', '.less', '.vue', '.svelte'
    }
    
    CONFIG_EXTENSIONS = {
        '.json', '.yaml', '.yml', '.toml', '.ini', '.env', '.config'
    }
    
    DOC_EXTENSIONS = {
        '.md', '.rst', '.txt', '.doc', '.docx'
    }
    
    IGNORE_PATTERNS = {
        '__pycache__', '.git', 'node_modules', '.venv', 'venv',
        '.pytest_cache', '.mypy_cache', 'dist', 'build', '.egg-info',
        '.DS_Store', 'Thumbs.db', '.log'
    }
    
    def __init__(self, callback: Callable[[ChangeEvent], None]):
        super().__init__()
        self.callback = callback
        self.change_buffer: Dict[str, ChangeEvent] = {}
        self.last_flush = time.time()
        self.buffer_timeout = 2.0  # Batch changes within 2 seconds
        
    def should_ignore(self, file_path: str) -> bool:
        """Check if file should be ignored"""
        path_parts = Path(file_path).parts
        return any(pattern in path_parts for pattern in self.IGNORE_PATTERNS)
    
    def get_file_category(self, file_path: str) -> str:
        """Categorize file type"""
        ext = Path(file_path).suffix.lower()
        if ext in self.CODE_EXTENSIONS:
            return 'code'
        elif ext in self.CONFIG_EXTENSIONS:
            return 'config'
        elif ext in self.DOC_EXTENSIONS:
            return 'documentation'
        else:
            return 'other'
    
    def create_change_event(self, event: FileSystemEvent, event_type: str) -> ChangeEvent:
        """Create standardized change event"""
        file_path = event.src_path
        ext = Path(file_path).suffix.lower()
        
        file_size = None
        try:
            if Path(file_path).exists():
                file_size = Path(file_path).stat().st_size
        except (OSError, PermissionError):
            pass
        
        return ChangeEvent(
            file_path=file_path,
            event_type=event_type,
            timestamp=datetime.now(),
            file_extension=ext,
            file_size=file_size,
            is_code_file=ext in self.CODE_EXTENSIONS
        )
    
    def buffer_change(self, change: ChangeEvent):
        """Buffer changes to avoid flooding"""
        # Use file path as key to deduplicate rapid changes
        self.change_buffer[change.file_path] = change
        
        # Flush buffer if timeout reached
        if time.time() - self.last_flush > self.buffer_timeout:
            self.flush_buffer()
    
    def flush_buffer(self):
        """Process buffered changes"""
        if not self.change_buffer:
            return
            
        changes = list(self.change_buffer.values())
        self.change_buffer.clear()
        self.last_flush = time.time()
        
        # Send batched changes to callback
        for change in changes:
            self.callback(change)
    
    def on_created(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            change = self.create_change_event(event, 'created')
            self.buffer_change(change)
    
    def on_modified(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            change = self.create_change_event(event, 'modified')
            self.buffer_change(change)
    
    def on_deleted(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            change = self.create_change_event(event, 'deleted')
            self.buffer_change(change)
    
    def on_moved(self, event):
        if not event.is_directory and not self.should_ignore(event.src_path):
            change = self.create_change_event(event, 'moved')
            self.buffer_change(change)

class ProjectWatcher:
    """Main project monitoring system"""
    
    def __init__(self, project_path: str, analysis_callback: Optional[Callable] = None):
        self.project_path = Path(project_path)
        self.analysis_callback = analysis_callback
        self.observer = Observer()
        self.is_running = False
        self.change_history: List[ChangeEvent] = []
        self.max_history = 1000
        
        # Statistics
        self.stats = {
            'total_changes': 0,
            'code_changes': 0,
            'config_changes': 0,
            'doc_changes': 0,
            'start_time': None
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def handle_change(self, change: ChangeEvent):
        """Process file change event"""
        self.change_history.append(change)
        
        # Trim history if too long
        if len(self.change_history) > self.max_history:
            self.change_history = self.change_history[-self.max_history:]
        
        # Update statistics
        self.stats['total_changes'] += 1
        if change.is_code_file:
            self.stats['code_changes'] += 1
        
        category = SmartFileHandler(lambda x: None).get_file_category(change.file_path)
        if category == 'config':
            self.stats['config_changes'] += 1
        elif category == 'documentation':
            self.stats['doc_changes'] += 1
        
        # Log important changes
        if change.is_code_file or category in ['config', 'documentation']:
            self.logger.info(f"📝 {change.event_type.upper()}: {Path(change.file_path).name}")
        
        # Trigger analysis if callback provided
        if self.analysis_callback and self.should_trigger_analysis(change):
            asyncio.create_task(self.analysis_callback(change))
    
    def should_trigger_analysis(self, change: ChangeEvent) -> bool:
        """Determine if change should trigger analysis"""
        # Always analyze code file changes
        if change.is_code_file:
            return True
        
        # Analyze config changes
        category = SmartFileHandler(lambda x: None).get_file_category(change.file_path)
        if category == 'config':
            return True
        
        # Analyze significant file size changes
        if change.file_size and change.file_size > 10000:  # > 10KB
            return True
        
        return False
    
    def start(self):
        """Start monitoring project"""
        if self.is_running:
            self.logger.warning("Project watcher already running")
            return
        
        handler = SmartFileHandler(self.handle_change)
        self.observer.schedule(handler, str(self.project_path), recursive=True)
        
        self.observer.start()
        self.is_running = True
        self.stats['start_time'] = datetime.now()
        
        self.logger.info(f"🔍 Started monitoring: {self.project_path}")
    
    def stop(self):
        """Stop monitoring"""
        if not self.is_running:
            return
        
        self.observer.stop()
        self.observer.join()
        self.is_running = False
        
        self.logger.info("🛑 Stopped project monitoring")
    
    def get_recent_changes(self, minutes: int = 10) -> List[ChangeEvent]:
        """Get recent changes within specified minutes"""
        cutoff_time = datetime.now().timestamp() - (minutes * 60)
        return [
            change for change in self.change_history
            if change.timestamp.timestamp() > cutoff_time
        ]
    
    def get_statistics(self) -> Dict:
        """Get monitoring statistics"""
        runtime = None
        if self.stats['start_time']:
            runtime = (datetime.now() - self.stats['start_time']).total_seconds()
        
        return {
            **self.stats,
            'runtime_seconds': runtime,
            'changes_per_minute': self.stats['total_changes'] / (runtime / 60) if runtime else 0,
            'is_running': self.is_running,
            'recent_changes_count': len(self.get_recent_changes())
        }
    
    def export_history(self, file_path: str):
        """Export change history to JSON"""
        data = {
            'export_time': datetime.now().isoformat(),
            'statistics': self.get_statistics(),
            'changes': [
                {
                    'file_path': change.file_path,
                    'event_type': change.event_type,
                    'timestamp': change.timestamp.isoformat(),
                    'file_extension': change.file_extension,
                    'file_size': change.file_size,
                    'is_code_file': change.is_code_file
                }
                for change in self.change_history
            ]
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 Exported history to: {file_path}")

# Example usage and testing
async def example_analysis_callback(change: ChangeEvent):
    """Example analysis callback"""
    print(f"🔬 ANALYZING: {change.file_path}")
    print(f"   Type: {change.event_type}")
    print(f"   Size: {change.file_size} bytes")
    print(f"   Code file: {change.is_code_file}")
    print(f"   Time: {change.timestamp}")
    print()

if __name__ == "__main__":
    # Test the project watcher
    watcher = ProjectWatcher(".", example_analysis_callback)
    
    try:
        watcher.start()
        print("🔍 Project watcher started. Make some file changes...")
        print("💡 Press Ctrl+C to stop")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
            
            # Print stats every 30 seconds
            if watcher.stats['total_changes'] > 0 and watcher.stats['total_changes'] % 10 == 0:
                stats = watcher.get_statistics()
                print(f"📊 Stats: {stats['total_changes']} total, {stats['code_changes']} code files")
    
    except KeyboardInterrupt:
        print("\n🛑 Stopping watcher...")
        watcher.stop()
        
        # Export final statistics
        final_stats = watcher.get_statistics()
        print(f"📈 Final stats: {final_stats}")
        
        if watcher.change_history:
            watcher.export_history("project_changes_history.json")
