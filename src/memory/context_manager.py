import json
import logging
from datetime import datetime
from typing import Dict, Any, List

class ContextManager:
    """Manages project context and memory layers"""
    
    def __init__(self):
        self.context = {}
        self.working_memory = {}
        self.episodic_memory = []
        self.logger = logging.getLogger(__name__)
        self.initialized_at = datetime.now()
        
    def update(self, key: str, value: Any):
        """Update working memory context"""
        self.context[key] = value
        self.working_memory[key] = {
            "value": value,
            "updated_at": datetime.now().isoformat()
        }
        self.logger.info(f"Context updated: {key}")
    
    def get(self, key: str, default=None):
        """Get value from context"""
        return self.context.get(key, default)
    
    def add_episode(self, episode: Dict[str, Any]):
        """Add episode to episodic memory"""
        episode["timestamp"] = datetime.now().isoformat()
        self.episodic_memory.append(episode)
        self.logger.info(f"Episode added: {episode.get('type', 'unknown')}")
    
    def get_recent_episodes(self, limit: int = 10) -> List[Dict]:
        """Get recent episodes from memory"""
        return self.episodic_memory[-limit:] if self.episodic_memory else []
    
    def summarize_context(self) -> Dict[str, Any]:
        """Get a summary of current context"""
        return {
            "working_memory_keys": list(self.context.keys()),
            "episodic_memory_count": len(self.episodic_memory),
            "initialized_at": self.initialized_at.isoformat(),
            "last_update": datetime.now().isoformat()
        }
    
    def export_context(self) -> str:
        """Export context as JSON string"""
        export_data = {
            "context": self.context,
            "working_memory": self.working_memory,
            "episodic_memory": self.episodic_memory,
            "summary": self.summarize_context()
        }
        return json.dumps(export_data, indent=2)
