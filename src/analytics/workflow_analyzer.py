"""
Workflow Analytics Engine for Kairos
Analyzes completed tasks and workflows to detect patterns and predict next steps.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
import json
import math
import asyncpg
import redis.asyncio as redis
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

@dataclass
class TaskPattern:
    """Represents a discovered task pattern"""
    pattern_id: str
    sequence: List[str]  # Sequence of task types
    frequency: int
    confidence: float
    avg_completion_time: float
    success_rate: float
    common_contexts: List[str]
    next_task_predictions: Dict[str, float]  # task_type -> probability

@dataclass
class WorkflowSuggestion:
    """Represents a workflow suggestion for the user"""
    suggestion_id: str
    current_task: str
    suggested_next_tasks: List[Dict[str, Any]]  # task, confidence, reasoning
    pattern_match: str
    confidence_score: float
    estimated_completion_time: float
    created_at: str

class WorkflowAnalyzer:
    """Analyzes workflow patterns and provides intelligent task suggestions"""
    
    def __init__(self, db_pool=None, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.redis_client = redis_client
        
        # Pattern detection parameters
        self.min_pattern_frequency = 3  # Minimum occurrences to consider a pattern
        self.pattern_window_size = 5    # Look at sequences of N tasks
        self.similarity_threshold = 0.7  # Cosine similarity threshold for grouping
        
        # Cache for patterns and suggestions
        self.patterns_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # ML models for pattern analysis
        self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
        self.kmeans = None
        
        # Pattern storage
        self.discovered_patterns = {}
        self.user_preferences = {}
        
        self.logger.info("🧠 Workflow Analyzer initialized")
    
    async def initialize(self):
        """Initialize the workflow analyzer with existing data"""
        if not self.db_pool:
            self.logger.warning("Workflow analyzer initialized without database connection")
            return
        
        await self._create_workflow_tables()
        await self._load_existing_patterns()
        await self._analyze_historical_workflows()
        
        self.logger.info("✅ Workflow analyzer initialized with historical data")
    
    async def _create_workflow_tables(self):
        """Create workflow analysis tables"""
        try:
            async with self.db_pool.acquire() as conn:
                # Task sequences table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS task_sequences (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR(255) NOT NULL,
                        project_id VARCHAR(255) NOT NULL,
                        session_id VARCHAR(255),
                        task_sequence JSONB NOT NULL,
                        completion_times JSONB NOT NULL,
                        success_flags JSONB NOT NULL,
                        context_data JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Discovered patterns table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_patterns (
                        pattern_id VARCHAR(255) PRIMARY KEY,
                        pattern_sequence JSONB NOT NULL,
                        frequency INTEGER NOT NULL DEFAULT 1,
                        confidence DECIMAL(5,4) NOT NULL DEFAULT 0.0,
                        avg_completion_time DECIMAL(10,2),
                        success_rate DECIMAL(5,4) NOT NULL DEFAULT 0.0,
                        common_contexts JSONB,
                        next_task_predictions JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # User workflow preferences
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_workflow_preferences (
                        user_id VARCHAR(255) PRIMARY KEY,
                        preferred_patterns JSONB,
                        avoided_patterns JSONB,
                        task_type_preferences JSONB,
                        avg_session_length INTEGER DEFAULT 0,
                        preferred_times JSONB,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Workflow suggestions log
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS workflow_suggestions_log (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        user_id VARCHAR(255) NOT NULL,
                        project_id VARCHAR(255) NOT NULL,
                        current_task VARCHAR(255) NOT NULL,
                        suggested_tasks JSONB NOT NULL,
                        pattern_match VARCHAR(255),
                        confidence_score DECIMAL(5,4),
                        user_action VARCHAR(50), -- 'accepted', 'rejected', 'modified', 'ignored'
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        responded_at TIMESTAMP WITH TIME ZONE
                    );
                """)
                
                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_task_sequences_user_project 
                    ON task_sequences(user_id, project_id);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_workflow_patterns_frequency 
                    ON workflow_patterns(frequency DESC);
                """)
                
                self.logger.info("✅ Workflow analysis tables created")
                
        except Exception as e:
            self.logger.error(f"Failed to create workflow tables: {e}")
            raise
    
    async def _load_existing_patterns(self):
        """Load existing patterns from database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                patterns = await conn.fetch("""
                    SELECT * FROM workflow_patterns 
                    WHERE frequency >= $1 
                    ORDER BY frequency DESC, confidence DESC
                """, self.min_pattern_frequency)
                
                for row in patterns:
                    pattern = TaskPattern(
                        pattern_id=row['pattern_id'],
                        sequence=json.loads(row['pattern_sequence']),
                        frequency=row['frequency'],
                        confidence=float(row['confidence']),
                        avg_completion_time=float(row['avg_completion_time'] or 0),
                        success_rate=float(row['success_rate']),
                        common_contexts=json.loads(row['common_contexts'] or '[]'),
                        next_task_predictions=json.loads(row['next_task_predictions'] or '{}')
                    )
                    
                    self.discovered_patterns[pattern.pattern_id] = pattern
                
                self.logger.info(f"📋 Loaded {len(self.discovered_patterns)} existing patterns")
                
        except Exception as e:
            self.logger.error(f"Failed to load existing patterns: {e}")
    
    async def _analyze_historical_workflows(self):
        """Analyze historical workflow data to discover patterns"""
        if not self.db_pool:
            return
        
        try:
            # Get recent task data for analysis
            async with self.db_pool.acquire() as conn:
                # Get task completion sequences from performance metrics
                tasks = await conn.fetch("""
                    SELECT 
                        COALESCE(project_id, 'default') as project_id,
                        COALESCE(session_id, 'default') as session_id,
                        task_type,
                        response_time_ms,
                        success,
                        created_at
                    FROM model_performance_metrics 
                    WHERE created_at >= $1
                    ORDER BY project_id, session_id, created_at
                """, datetime.now() - timedelta(days=30))
                
                # Group tasks by session
                sessions = defaultdict(list)
                for task in tasks:
                    session_key = f"{task['project_id']}_{task['session_id']}"
                    sessions[session_key].append({
                        'task_type': task['task_type'],
                        'completion_time': task['response_time_ms'] / 1000,  # Convert to seconds
                        'success': task['success'],
                        'timestamp': task['created_at']
                    })
                
                # Analyze each session for patterns
                new_patterns = 0
                for session_key, task_list in sessions.items():
                    if len(task_list) >= 2:  # Need at least 2 tasks for a pattern
                        patterns = await self._extract_patterns_from_session(task_list)
                        for pattern in patterns:
                            if await self._store_or_update_pattern(pattern):
                                new_patterns += 1
                
                self.logger.info(f"🔍 Analyzed {len(sessions)} sessions, discovered {new_patterns} new patterns")
                
        except Exception as e:
            self.logger.error(f"Failed to analyze historical workflows: {e}")
    
    async def _extract_patterns_from_session(self, tasks: List[Dict]) -> List[TaskPattern]:
        """Extract patterns from a single session"""
        patterns = []
        
        if len(tasks) < 2:
            return patterns
        
        # Extract sequences of different lengths
        for window_size in range(2, min(len(tasks) + 1, self.pattern_window_size + 1)):
            for i in range(len(tasks) - window_size + 1):
                window = tasks[i:i + window_size]
                
                # Create pattern from window
                sequence = [task['task_type'] for task in window]
                completion_times = [task['completion_time'] for task in window]
                success_flags = [task['success'] for task in window]
                
                # Generate pattern ID
                pattern_id = f"pattern_{hash(tuple(sequence))}"
                
                # Calculate metrics
                avg_completion_time = sum(completion_times) / len(completion_times)
                success_rate = sum(success_flags) / len(success_flags)
                
                # Predict next task if there's more data
                next_task_predictions = {}
                if i + window_size < len(tasks):
                    next_task = tasks[i + window_size]['task_type']
                    next_task_predictions[next_task] = 1.0
                
                pattern = TaskPattern(
                    pattern_id=pattern_id,
                    sequence=sequence,
                    frequency=1,
                    confidence=success_rate,
                    avg_completion_time=avg_completion_time,
                    success_rate=success_rate,
                    common_contexts=[],
                    next_task_predictions=next_task_predictions
                )
                
                patterns.append(pattern)
        
        return patterns
    
    async def _store_or_update_pattern(self, pattern: TaskPattern) -> bool:
        """Store a new pattern or update existing one"""
        if not self.db_pool:
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                # Check if pattern exists
                existing = await conn.fetchrow("""
                    SELECT frequency, confidence, avg_completion_time, success_rate, next_task_predictions
                    FROM workflow_patterns WHERE pattern_id = $1
                """, pattern.pattern_id)
                
                if existing:
                    # Update existing pattern
                    new_frequency = existing['frequency'] + 1
                    
                    # Update weighted averages
                    old_weight = existing['frequency']
                    new_weight = 1
                    total_weight = old_weight + new_weight
                    
                    new_confidence = (
                        (existing['confidence'] * old_weight + pattern.confidence * new_weight) 
                        / total_weight
                    )
                    
                    new_avg_time = (
                        (existing['avg_completion_time'] * old_weight + pattern.avg_completion_time * new_weight)
                        / total_weight
                    )
                    
                    new_success_rate = (
                        (existing['success_rate'] * old_weight + pattern.success_rate * new_weight)
                        / total_weight
                    )
                    
                    # Merge next task predictions
                    old_predictions = json.loads(existing['next_task_predictions'] or '{}')
                    new_predictions = pattern.next_task_predictions
                    
                    merged_predictions = old_predictions.copy()
                    for task, prob in new_predictions.items():
                        if task in merged_predictions:
                            merged_predictions[task] = (merged_predictions[task] + prob) / 2
                        else:
                            merged_predictions[task] = prob
                    
                    await conn.execute("""
                        UPDATE workflow_patterns 
                        SET frequency = $2, confidence = $3, avg_completion_time = $4,
                            success_rate = $5, next_task_predictions = $6, updated_at = CURRENT_TIMESTAMP
                        WHERE pattern_id = $1
                    """, pattern.pattern_id, new_frequency, new_confidence, new_avg_time,
                        new_success_rate, json.dumps(merged_predictions))
                    
                    # Update in-memory cache
                    if pattern.pattern_id in self.discovered_patterns:
                        self.discovered_patterns[pattern.pattern_id].frequency = new_frequency
                        self.discovered_patterns[pattern.pattern_id].confidence = new_confidence
                    
                    return False  # Not a new pattern
                    
                else:
                    # Insert new pattern
                    await conn.execute("""
                        INSERT INTO workflow_patterns 
                        (pattern_id, pattern_sequence, frequency, confidence, avg_completion_time,
                         success_rate, next_task_predictions)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, pattern.pattern_id, json.dumps(pattern.sequence), pattern.frequency,
                        pattern.confidence, pattern.avg_completion_time, pattern.success_rate,
                        json.dumps(pattern.next_task_predictions))
                    
                    # Add to in-memory cache
                    self.discovered_patterns[pattern.pattern_id] = pattern
                    
                    return True  # New pattern
                    
        except Exception as e:
            self.logger.error(f"Failed to store/update pattern: {e}")
            return False
    
    async def record_task_completion(
        self, 
        user_id: str, 
        project_id: str, 
        task_type: str, 
        completion_time: float,
        success: bool,
        session_id: str = None,
        context: Dict[str, Any] = None
    ):
        """Record a completed task for pattern analysis"""
        if not self.db_pool:
            return
        
        try:
            # Get recent tasks from this session for pattern detection
            session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d_%H')}"
            
            async with self.db_pool.acquire() as conn:
                # Get recent tasks from this session
                recent_tasks = await conn.fetch("""
                    SELECT task_type, completion_time, success 
                    FROM (
                        SELECT 
                            unnest(sequence) as task_type,
                            unnest(completion_times) as completion_time,
                            unnest(success_flags) as success
                        FROM task_sequences 
                        WHERE user_id = $1 AND project_id = $2 AND session_id = $3
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) recent
                    UNION ALL
                    SELECT $4, $5, $6
                """, user_id, project_id, session_id, task_type, completion_time, success)
                
                # Update or create task sequence
                task_list = [dict(row) for row in recent_tasks]
                task_types = [task['task_type'] for task in task_list]
                completion_times = [float(task['completion_time']) for task in task_list]
                success_flags = [bool(task['success']) for task in task_list]
                
                await conn.execute("""
                    INSERT INTO task_sequences 
                    (user_id, project_id, session_id, task_sequence, completion_times, success_flags, context_data)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (user_id, project_id, session_id) DO UPDATE
                    SET task_sequence = $4, completion_times = $5, success_flags = $6,
                        context_data = $7, created_at = CURRENT_TIMESTAMP
                """, user_id, project_id, session_id, 
                    json.dumps(task_types), json.dumps(completion_times), 
                    json.dumps(success_flags), json.dumps(context or {}))
                
                # Analyze for new patterns if we have enough tasks
                if len(task_list) >= 2:
                    patterns = await self._extract_patterns_from_session(task_list)
                    for pattern in patterns:
                        await self._store_or_update_pattern(pattern)
                
                self.logger.debug(f"📝 Recorded task completion: {task_type} for {user_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to record task completion: {e}")
    
    async def get_workflow_suggestions(
        self, 
        user_id: str, 
        project_id: str, 
        current_task: str,
        session_context: Dict[str, Any] = None,
        limit: int = 3
    ) -> List[WorkflowSuggestion]:
        """Get workflow suggestions based on current task and patterns"""
        
        # Check cache first
        cache_key = f"workflow_suggestions:{user_id}:{project_id}:{current_task}"
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [WorkflowSuggestion(**item) for item in data]
            except Exception as e:
                self.logger.debug(f"Cache lookup failed: {e}")
        
        suggestions = []
        
        try:
            # Find patterns that match current context
            matching_patterns = []
            
            for pattern_id, pattern in self.discovered_patterns.items():
                # Check if current task appears in this pattern
                if current_task in pattern.sequence:
                    # Find position of current task in pattern
                    for i, task in enumerate(pattern.sequence):
                        if task == current_task and i < len(pattern.sequence) - 1:
                            # We can suggest next task(s) from this pattern
                            next_task = pattern.sequence[i + 1]
                            confidence = pattern.confidence * (pattern.frequency / 10)  # Scale by frequency
                            
                            matching_patterns.append({
                                'pattern': pattern,
                                'next_task': next_task,
                                'confidence': min(confidence, 1.0),
                                'position': i
                            })
            
            # Sort by confidence and frequency
            matching_patterns.sort(key=lambda x: (x['confidence'], x['pattern'].frequency), reverse=True)
            
            # Generate suggestions
            for i, match in enumerate(matching_patterns[:limit]):
                pattern = match['pattern']
                next_task = match['next_task']
                
                # Calculate reasoning
                reasoning = self._generate_suggestion_reasoning(pattern, match['position'], current_task)
                
                suggestion = WorkflowSuggestion(
                    suggestion_id=f"sug_{user_id}_{int(datetime.now().timestamp())}_{i}",
                    current_task=current_task,
                    suggested_next_tasks=[{
                        'task': next_task,
                        'confidence': match['confidence'],
                        'reasoning': reasoning,
                        'estimated_time': pattern.avg_completion_time
                    }],
                    pattern_match=pattern.pattern_id,
                    confidence_score=match['confidence'],
                    estimated_completion_time=pattern.avg_completion_time,
                    created_at=datetime.now().isoformat()
                )
                
                suggestions.append(suggestion)
            
            # If no pattern-based suggestions, provide general ones
            if not suggestions:
                suggestions = await self._get_general_suggestions(current_task, user_id, project_id)
            
            # Cache the suggestions
            if self.redis_client and suggestions:
                try:
                    cache_data = [asdict(sug) for sug in suggestions]
                    await self.redis_client.setex(
                        cache_key, 
                        self.cache_ttl, 
                        json.dumps(cache_data)
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to cache suggestions: {e}")
            
            # Log the suggestion for later analysis
            if suggestions and self.db_pool:
                await self._log_workflow_suggestion(user_id, project_id, suggestions[0])
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to get workflow suggestions: {e}")
            return []
    
    def _generate_suggestion_reasoning(self, pattern: TaskPattern, position: int, current_task: str) -> str:
        """Generate human-readable reasoning for a suggestion"""
        frequency_desc = "frequently" if pattern.frequency > 10 else "sometimes" if pattern.frequency > 3 else "occasionally"
        
        success_desc = "successful" if pattern.success_rate > 0.8 else "moderately successful" if pattern.success_rate > 0.6 else "variable success"
        
        time_desc = "quick" if pattern.avg_completion_time < 30 else "moderate" if pattern.avg_completion_time < 120 else "longer"
        
        return (
            f"This suggestion is based on a pattern that appears {frequency_desc} "
            f"in workflows with {success_desc} outcomes. "
            f"Tasks in this sequence typically take a {time_desc} time to complete. "
            f"After '{current_task}', users often proceed with this next step."
        )
    
    async def _get_general_suggestions(self, current_task: str, user_id: str, project_id: str) -> List[WorkflowSuggestion]:
        """Get general suggestions when no specific patterns match"""
        # These are fallback suggestions based on common workflow logic
        general_suggestions = {
            'coding': ['testing', 'documentation', 'code_review'],
            'testing': ['debugging', 'optimization', 'deployment'],
            'debugging': ['testing', 'documentation', 'code_review'],
            'research': ['analysis', 'documentation', 'presentation'],
            'analysis': ['reporting', 'visualization', 'documentation'],
            'documentation': ['review', 'publishing', 'maintenance']
        }
        
        suggestions = []
        task_type = current_task.lower()
        
        # Find matching general category
        for category, next_tasks in general_suggestions.items():
            if category in task_type or any(word in task_type for word in category.split('_')):
                for i, next_task in enumerate(next_tasks[:2]):  # Limit to 2 general suggestions
                    suggestion = WorkflowSuggestion(
                        suggestion_id=f"gen_{user_id}_{int(datetime.now().timestamp())}_{i}",
                        current_task=current_task,
                        suggested_next_tasks=[{
                            'task': next_task,
                            'confidence': 0.6 - (i * 0.1),  # Decreasing confidence
                            'reasoning': f"Commonly follows {category} tasks in typical workflows",
                            'estimated_time': 60.0  # Default estimate
                        }],
                        pattern_match="general_workflow",
                        confidence_score=0.6 - (i * 0.1),
                        estimated_completion_time=60.0,
                        created_at=datetime.now().isoformat()
                    )
                    suggestions.append(suggestion)
                break
        
        return suggestions[:2]  # Return max 2 general suggestions
    
    async def _log_workflow_suggestion(self, user_id: str, project_id: str, suggestion: WorkflowSuggestion):
        """Log workflow suggestion for later analysis"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO workflow_suggestions_log 
                    (user_id, project_id, current_task, suggested_tasks, pattern_match, confidence_score)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, user_id, project_id, suggestion.current_task,
                    json.dumps(suggestion.suggested_next_tasks), suggestion.pattern_match,
                    suggestion.confidence_score)
        except Exception as e:
            self.logger.error(f"Failed to log workflow suggestion: {e}")
    
    async def record_suggestion_feedback(
        self, 
        user_id: str, 
        suggestion_id: str, 
        action: str  # 'accepted', 'rejected', 'modified', 'ignored'
    ):
        """Record user feedback on suggestions for learning"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    UPDATE workflow_suggestions_log 
                    SET user_action = $1, responded_at = CURRENT_TIMESTAMP
                    WHERE id = (
                        SELECT id FROM workflow_suggestions_log 
                        WHERE user_id = $2 AND id::text LIKE $3 
                        ORDER BY created_at DESC LIMIT 1
                    )
                """, action, user_id, f"%{suggestion_id[-8:]}%")  # Match last 8 chars of suggestion_id
                
                self.logger.info(f"📊 Recorded suggestion feedback: {action} for {suggestion_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to record suggestion feedback: {e}")
    
    async def get_workflow_analytics(self, user_id: str = None, project_id: str = None, days: int = 30) -> Dict[str, Any]:
        """Get workflow analytics and insights"""
        if not self.db_pool:
            return {"error": "No database connection"}
        
        try:
            async with self.db_pool.acquire() as conn:
                # Base query conditions
                where_conditions = ["created_at >= $1"]
                params = [datetime.now() - timedelta(days=days)]
                
                if user_id:
                    where_conditions.append("user_id = $2")
                    params.append(user_id)
                    
                if project_id:
                    where_conditions.append("project_id = $3")
                    params.append(project_id)
                
                where_clause = " AND ".join(where_conditions)
                
                # Most common patterns
                top_patterns = await conn.fetch(f"""
                    SELECT pattern_id, pattern_sequence, frequency, confidence, success_rate
                    FROM workflow_patterns 
                    WHERE frequency >= $1
                    ORDER BY frequency DESC, confidence DESC
                    LIMIT 10
                """, self.min_pattern_frequency)
                
                # Suggestion acceptance rate
                suggestion_stats = await conn.fetchrow(f"""
                    SELECT 
                        COUNT(*) as total_suggestions,
                        COUNT(CASE WHEN user_action = 'accepted' THEN 1 END) as accepted,
                        COUNT(CASE WHEN user_action = 'rejected' THEN 1 END) as rejected,
                        AVG(confidence_score) as avg_confidence
                    FROM workflow_suggestions_log
                    WHERE {where_clause}
                """, *params)
                
                # Most productive patterns (high success rate + frequency)
                productive_patterns = await conn.fetch("""
                    SELECT pattern_id, pattern_sequence, 
                           (frequency * success_rate) as productivity_score,
                           avg_completion_time
                    FROM workflow_patterns 
                    WHERE frequency >= $1 AND success_rate > 0.7
                    ORDER BY productivity_score DESC
                    LIMIT 5
                """, self.min_pattern_frequency)
                
                return {
                    "period_days": days,
                    "user_id": user_id,
                    "project_id": project_id,
                    "total_patterns": len(self.discovered_patterns),
                    "top_patterns": [
                        {
                            "pattern_id": row['pattern_id'],
                            "sequence": json.loads(row['pattern_sequence']),
                            "frequency": row['frequency'],
                            "confidence": float(row['confidence']),
                            "success_rate": float(row['success_rate'])
                        }
                        for row in top_patterns
                    ],
                    "suggestion_stats": {
                        "total_suggestions": suggestion_stats['total_suggestions'] or 0,
                        "acceptance_rate": (
                            suggestion_stats['accepted'] / suggestion_stats['total_suggestions']
                            if suggestion_stats['total_suggestions'] > 0 else 0
                        ),
                        "rejection_rate": (
                            suggestion_stats['rejected'] / suggestion_stats['total_suggestions']
                            if suggestion_stats['total_suggestions'] > 0 else 0
                        ),
                        "avg_confidence": float(suggestion_stats['avg_confidence'] or 0)
                    },
                    "most_productive_patterns": [
                        {
                            "pattern_id": row['pattern_id'],
                            "sequence": json.loads(row['pattern_sequence']),
                            "productivity_score": float(row['productivity_score']),
                            "avg_completion_time": float(row['avg_completion_time'] or 0)
                        }
                        for row in productive_patterns
                    ],
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get workflow analytics: {e}")
            return {"error": str(e)}

# Global workflow analyzer instance
workflow_analyzer = None

async def get_workflow_analyzer() -> WorkflowAnalyzer:
    """Get global workflow analyzer instance"""
    global workflow_analyzer
    if workflow_analyzer is None:
        workflow_analyzer = WorkflowAnalyzer()
        await workflow_analyzer.initialize()
    return workflow_analyzer
