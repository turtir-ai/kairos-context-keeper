import asyncio
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path
import uuid
from enum import Enum

from src.agents.base_agent import BaseAgent
from src.api.websocket_manager import websocket_manager, WebSocketMessage, MessageType
from src.monitoring.performance_tracker import performance_tracker
from src.monitoring.system_health import system_health_monitor
from src.core.anomaly_detector import get_anomaly_detector
from src.core.proactive_analyzer import proactive_analyzer

# Try to import code analysis modules
try:
    from src.core.code_parser import CodeParser
    from src.memory.ast_converter import ASTConverter
    CODE_ANALYSIS_AVAILABLE = True
except ImportError:
    CODE_ANALYSIS_AVAILABLE = False
    print("⚠️  Code analysis modules not available")

class ActionType(Enum):
    """Types of actions that can be suggested"""
    REFACTOR = "refactor"
    CREATE_TASK = "create_task"
    FIX_CODE = "fix_code"
    OPTIMIZE = "optimize"
    DOCUMENT = "document"
    TEST = "test"
    SECURITY = "security"

@dataclass
class ActionableSuggestion:
    """Represents an actionable suggestion with evidence and implementation details"""
    id: str
    title: str
    description: str
    action_type: ActionType
    priority: str  # "low", "medium", "high", "critical"
    evidence: List[Dict[str, Any]]  # Supporting evidence from analysis
    implementation_plan: List[str]  # Step-by-step implementation
    affected_files: List[str]
    estimated_effort: str  # "5 min", "30 min", "2 hours", etc.
    benefits: List[str]
    risks: List[str]
    can_auto_apply: bool
    created_at: datetime
    status: str = "pending"  # "pending", "approved", "applied", "dismissed"

class EnhancedSupervisorAgent(BaseAgent):
    """Enhanced Supervisor Agent with actionable suggestions and proactive analysis"""

    def __init__(self, name="EnhancedSupervisor", mcp_context=None):
        super().__init__(name=name, mcp_context=mcp_context)
        self.anomaly_detector = None
        self.code_parser = None
        self.ast_converter = None
        self.monitoring_active = True
        
        # Store suggestions with detailed tracking
        self.actionable_suggestions = {}  # id -> ActionableSuggestion
        self.suggestion_history = deque(maxlen=200)
        self.analysis_cache = {}  # Cache for expensive analyses
        
        # Analysis scheduling
        self.last_full_analysis = None
        self.analysis_interval = timedelta(hours=1)  # Full analysis every hour
        
        # Initialize code analysis if available
        if CODE_ANALYSIS_AVAILABLE:
            self.code_parser = CodeParser()
            self.ast_converter = ASTConverter()

    async def initialize(self):
        """Initialize Enhanced Supervisor Agent and its components"""
        self.anomaly_detector = await get_anomaly_detector()
        self.set_websocket_manager(websocket_manager)
        self.logger.info("Enhanced Supervisor Agent initialized")
        
        # Start proactive analysis loop
        asyncio.create_task(self.proactive_analysis_loop())
        await self.broadcast_status("initialized")

    async def proactive_analysis_loop(self):
        """Main loop for proactive analysis and suggestion generation"""
        while self.monitoring_active:
            try:
                await self.perform_proactive_analysis()
                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                self.logger.error(f"Error in proactive analysis loop: {e}")
                await asyncio.sleep(60)  # Shorter sleep on error

    async def perform_proactive_analysis(self):
        """Perform comprehensive proactive analysis and generate actionable suggestions"""
        self.logger.info("🔍 Starting proactive analysis...")
        
        # Check if we need a full analysis
        need_full_analysis = (
            self.last_full_analysis is None or 
            datetime.now() - self.last_full_analysis > self.analysis_interval
        )
        
        if need_full_analysis:
            await self.full_codebase_analysis()
            self.last_full_analysis = datetime.now()
        
        # Always check for immediate issues
        await self.check_immediate_issues()
        
        # Generate new suggestions based on findings
        await self.generate_actionable_suggestions()

    async def full_codebase_analysis(self):
        """Perform full codebase analysis to identify issues and opportunities"""
        if not CODE_ANALYSIS_AVAILABLE:
            return
        
        self.logger.info("🔍 Performing full codebase analysis...")
        
        try:
            # Parse all code files in the project
            project_root = Path.cwd()
            code_files = []
            
            # Find all Python files
            for pattern in ["**/*.py", "**/*.js", "**/*.ts"]:
                code_files.extend(project_root.glob(pattern))
            
            analysis_results = {
                'dead_functions': [],
                'circular_dependencies': [],
                'complex_functions': [],
                'security_issues': [],
                'documentation_gaps': [],
                'test_coverage_gaps': []
            }
            
            # Analyze each file
            for file_path in code_files[:50]:  # Limit to first 50 files for performance
                try:
                    if file_path.suffix == '.py':
                        file_analysis = await self.analyze_python_file(file_path)
                        self.merge_analysis_results(analysis_results, file_analysis)
                except Exception as e:
                    self.logger.warning(f"Failed to analyze {file_path}: {e}")
            
            # Cache results
            self.analysis_cache['full_analysis'] = {
                'results': analysis_results,
                'timestamp': datetime.now(),
                'files_analyzed': len(code_files)
            }
            
            self.logger.info(f"✅ Full analysis completed: {len(code_files)} files analyzed")
            
        except Exception as e:
            self.logger.error(f"Error in full codebase analysis: {e}")

    async def analyze_python_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a single Python file for issues and opportunities"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse AST
            ast_data = self.code_parser.parse_file(str(file_path))
            
            analysis = {
                'dead_functions': [],
                'complex_functions': [],
                'security_issues': [],
                'documentation_gaps': [],
                'test_coverage_gaps': []
            }
            
            # Analyze functions
            for node in ast_data.get('functions', []):
                func_name = node.get('name', '')
                
                # Check for dead code (simplified heuristic)
                if self.is_potentially_dead_function(func_name, content, file_path):
                    analysis['dead_functions'].append({
                        'function': func_name,
                        'file': str(file_path),
                        'line': node.get('line_start', 0)
                    })
                
                # Check complexity
                if self.is_complex_function(node):
                    analysis['complex_functions'].append({
                        'function': func_name,
                        'file': str(file_path),
                        'complexity_score': node.get('line_end', 0) - node.get('line_start', 0),
                        'line': node.get('line_start', 0)
                    })
                
                # Check documentation
                if not node.get('docstring') and not func_name.startswith('_'):
                    analysis['documentation_gaps'].append({
                        'function': func_name,
                        'file': str(file_path),
                        'line': node.get('line_start', 0)
                    })
            
            # Check for security issues (basic patterns)
            security_issues = self.check_security_patterns(content, file_path)
            analysis['security_issues'].extend(security_issues)
            
            return analysis
            
        except Exception as e:
            self.logger.warning(f"Error analyzing {file_path}: {e}")
            return {}

    def is_potentially_dead_function(self, func_name: str, content: str, file_path: Path) -> bool:
        """Simple heuristic to detect potentially dead functions"""
        # Skip common patterns that are likely not dead code
        if (func_name.startswith('test_') or 
            func_name in ['main', '__init__', '__str__', '__repr__'] or
            func_name.startswith('_')):
            return False
        
        # Count references to this function
        import re
        pattern = rf'\b{re.escape(func_name)}\b'
        matches = re.findall(pattern, content)
        
        # If function is only mentioned once (its definition), it might be dead
        return len(matches) <= 1

    def is_complex_function(self, node: Dict[str, Any]) -> bool:
        """Check if function is complex based on simple metrics"""
        line_count = node.get('line_end', 0) - node.get('line_start', 0)
        return line_count > 50  # Functions longer than 50 lines

    def check_security_patterns(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Check for basic security anti-patterns"""
        issues = []
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            line_lower = line.lower()
            
            # Check for hardcoded secrets (very basic)
            if any(pattern in line_lower for pattern in ['password=', 'api_key=', 'secret=']):
                if not any(safe in line_lower for safe in ['none', 'null', 'env', 'config']):
                    issues.append({
                        'type': 'hardcoded_secret',
                        'file': str(file_path),
                        'line': i,
                        'content': line.strip()
                    })
            
            # Check for SQL injection risks
            if 'execute(' in line_lower and ('%s' in line or '{' in line):
                issues.append({
                    'type': 'sql_injection_risk',
                    'file': str(file_path),
                    'line': i,
                    'content': line.strip()
                })
        
        return issues

    def merge_analysis_results(self, main_results: Dict, file_results: Dict):
        """Merge file analysis results into main results"""
        for key in main_results:
            if key in file_results:
                main_results[key].extend(file_results[key])

    async def check_immediate_issues(self):
        """Check for immediate issues that need attention"""
        # Check system health
        health_status = system_health_monitor.get_current_status()
        
        if health_status.get('status') != 'healthy':
            await self.create_system_health_suggestion(health_status)
        
        # Check performance metrics
        metrics = performance_tracker.get_metrics_summary()
        if self.has_performance_issues(metrics):
            await self.create_performance_suggestion(metrics)

    async def generate_actionable_suggestions(self):
        """Generate actionable suggestions based on analysis results"""
        if 'full_analysis' not in self.analysis_cache:
            return
        
        analysis = self.analysis_cache['full_analysis']['results']
        
        # Generate suggestions for dead code
        if analysis['dead_functions']:
            await self.create_dead_code_suggestion(analysis['dead_functions'])
        
        # Generate suggestions for complex functions
        if analysis['complex_functions']:
            await self.create_complexity_suggestion(analysis['complex_functions'])
        
        # Generate suggestions for security issues
        if analysis['security_issues']:
            await self.create_security_suggestion(analysis['security_issues'])
        
        # Generate suggestions for documentation gaps
        if analysis['documentation_gaps']:
            await self.create_documentation_suggestion(analysis['documentation_gaps'])

    async def create_dead_code_suggestion(self, dead_functions: List[Dict[str, Any]]):
        """Create suggestion for removing dead code"""
        if len(dead_functions) < 3:  # Only suggest if we have multiple instances
            return
        
        suggestion = ActionableSuggestion(
            id=str(uuid.uuid4()),
            title=f"Remove {len(dead_functions)} potentially unused functions",
            description=f"Found {len(dead_functions)} functions that appear to be unused. Removing dead code improves maintainability and reduces technical debt.",
            action_type=ActionType.REFACTOR,
            priority="medium",
            evidence=[
                {
                    "type": "dead_function",
                    "function": func['function'],
                    "file": func['file'],
                    "line": func['line']
                } for func in dead_functions[:5]  # Show first 5 as evidence
            ],
            implementation_plan=[
                "1. Verify functions are truly unused by searching for references",
                "2. Check if functions are part of public API",
                "3. Remove unused functions one by one",
                "4. Run tests to ensure no breakage",
                "5. Commit changes with descriptive message"
            ],
            affected_files=list(set(func['file'] for func in dead_functions)),
            estimated_effort="30-60 minutes",
            benefits=[
                "Reduced codebase size",
                "Improved maintainability",
                "Better code clarity",
                "Reduced technical debt"
            ],
            risks=[
                "Functions might be used dynamically",
                "Functions might be part of external API",
                "Risk of breaking existing functionality"
            ],
            can_auto_apply=False,  # Manual verification needed
            created_at=datetime.now()
        )
        
        await self.add_suggestion(suggestion)

    async def create_complexity_suggestion(self, complex_functions: List[Dict[str, Any]]):
        """Create suggestion for refactoring complex functions"""
        if not complex_functions:
            return
        
        # Sort by complexity and take top 3
        complex_functions.sort(key=lambda x: x['complexity_score'], reverse=True)
        top_complex = complex_functions[:3]
        
        suggestion = ActionableSuggestion(
            id=str(uuid.uuid4()),
            title=f"Refactor {len(top_complex)} overly complex functions",
            description=f"Found {len(complex_functions)} functions with high complexity. Breaking them down improves readability and maintainability.",
            action_type=ActionType.REFACTOR,
            priority="medium",
            evidence=[
                {
                    "type": "complex_function",
                    "function": func['function'],
                    "file": func['file'],
                    "line": func['line'],
                    "complexity_score": func['complexity_score']
                } for func in top_complex
            ],
            implementation_plan=[
                "1. Analyze function responsibilities",
                "2. Identify logical sub-functions",
                "3. Extract helper functions",
                "4. Simplify main function logic", 
                "5. Add comprehensive tests",
                "6. Update documentation"
            ],
            affected_files=list(set(func['file'] for func in top_complex)),
            estimated_effort="2-4 hours",
            benefits=[
                "Improved code readability",
                "Better testability",
                "Easier maintenance",
                "Reduced bug potential"
            ],
            risks=[
                "Risk of introducing bugs during refactoring",
                "Potential performance impact",
                "Breaking existing interfaces"
            ],
            can_auto_apply=False,
            created_at=datetime.now()
        )
        
        await self.add_suggestion(suggestion)

    async def create_security_suggestion(self, security_issues: List[Dict[str, Any]]):
        """Create suggestion for fixing security issues"""
        if not security_issues:
            return
        
        # Group by type
        issue_counts = {}
        for issue in security_issues:
            issue_type = issue['type']
            issue_counts[issue_type] = issue_counts.get(issue_type, 0) + 1
        
        suggestion = ActionableSuggestion(
            id=str(uuid.uuid4()),
            title=f"Fix {len(security_issues)} potential security issues",
            description=f"Found potential security vulnerabilities: {', '.join(f'{count} {issue_type}' for issue_type, count in issue_counts.items())}",
            action_type=ActionType.SECURITY,
            priority="high",
            evidence=[
                {
                    "type": "security_issue",
                    "issue_type": issue['type'],
                    "file": issue['file'],
                    "line": issue['line'],
                    "content": issue['content']
                } for issue in security_issues[:10]  # Show first 10
            ],
            implementation_plan=[
                "1. Review each flagged line for actual vulnerabilities",
                "2. Replace hardcoded secrets with environment variables",
                "3. Use parameterized queries for SQL operations",
                "4. Implement proper input validation",
                "5. Run security scan to verify fixes"
            ],
            affected_files=list(set(issue['file'] for issue in security_issues)),
            estimated_effort="1-3 hours",
            benefits=[
                "Improved application security",
                "Reduced risk of data breaches",
                "Better compliance with security standards",
                "Increased user trust"
            ],
            risks=[
                "False positives may waste time",
                "Changes might affect functionality",
                "Need thorough testing after fixes"
            ],
            can_auto_apply=False,
            created_at=datetime.now()
        )
        
        await self.add_suggestion(suggestion)

    async def create_documentation_suggestion(self, doc_gaps: List[Dict[str, Any]]):
        """Create suggestion for improving documentation"""
        if len(doc_gaps) < 5:  # Only suggest if we have multiple gaps
            return
        
        suggestion = ActionableSuggestion(
            id=str(uuid.uuid4()),
            title=f"Add documentation to {len(doc_gaps)} functions",
            description=f"Found {len(doc_gaps)} functions without docstrings. Proper documentation improves code maintainability.",
            action_type=ActionType.DOCUMENT,
            priority="low",
            evidence=[
                {
                    "type": "missing_docstring",
                    "function": gap['function'],
                    "file": gap['file'],
                    "line": gap['line']
                } for gap in doc_gaps[:10]
            ],
            implementation_plan=[
                "1. Review each function's purpose and parameters",
                "2. Add comprehensive docstrings following PEP 257",
                "3. Include parameter descriptions and return values",
                "4. Add usage examples where helpful",
                "5. Run documentation linter to verify format"
            ],
            affected_files=list(set(gap['file'] for gap in doc_gaps)),
            estimated_effort="1-2 hours",
            benefits=[
                "Improved code documentation",
                "Better developer onboarding",
                "Easier code maintenance",
                "Professional code appearance"
            ],
            risks=[
                "Time investment with no immediate functional benefit",
                "Documentation might become outdated"
            ],
            can_auto_apply=True,  # Could be automated
            created_at=datetime.now()
        )
        
        await self.add_suggestion(suggestion)

    async def add_suggestion(self, suggestion: ActionableSuggestion):
        """Add a new actionable suggestion"""
        # Check for duplicates
        for existing_id, existing in self.actionable_suggestions.items():
            if (existing.title == suggestion.title and 
                existing.status == "pending"):
                self.logger.debug(f"Skipping duplicate suggestion: {suggestion.title}")
                return
        
        # Add to active suggestions
        self.actionable_suggestions[suggestion.id] = suggestion
        self.suggestion_history.append(suggestion)
        
        # 🎯 AUTO TASK CREATION - Sprint 9 Requirement
        # For high priority suggestions or auto-applicable ones, create tasks automatically
        if suggestion.priority in ["high", "critical"] or suggestion.can_auto_apply:
            self.logger.info(f"🎯 Auto task criteria met for suggestion {suggestion.id}: priority={suggestion.priority}, can_auto_apply={suggestion.can_auto_apply}")
            await self.create_automatic_task(suggestion)
        else:
            self.logger.info(f"🔄 No auto task for suggestion {suggestion.id}: priority={suggestion.priority}, can_auto_apply={suggestion.can_auto_apply}")
        
        # Broadcast to frontend
        await self.broadcast_suggestion(suggestion)
        
        self.logger.info(f"✨ New actionable suggestion: {suggestion.title}")

    async def broadcast_suggestion(self, suggestion: ActionableSuggestion):
        """Broadcast new suggestion to connected clients"""
        from src.api.websocket_manager import WebSocketMessage, MessageType
        
        suggestion_data = {
            "id": suggestion.id,
            "title": suggestion.title,
            "description": suggestion.description,
            "action_type": suggestion.action_type.value,
            "priority": suggestion.priority,
            "evidence": suggestion.evidence[:3],  # Limit evidence for UI
            "implementation_plan": suggestion.implementation_plan,
            "affected_files": suggestion.affected_files,
            "estimated_effort": suggestion.estimated_effort,
            "benefits": suggestion.benefits,
            "risks": suggestion.risks,
            "can_auto_apply": suggestion.can_auto_apply,
            "created_at": suggestion.created_at.isoformat(),
            "status": suggestion.status
        }
        
        message = WebSocketMessage(
            message_type=MessageType.AGENT_STATUS,  # Using AGENT_STATUS for suggestions
            data=suggestion_data,
            timestamp=datetime.now()
        )
        await self.websocket_manager.broadcast_message(message)

    def has_performance_issues(self, metrics: Dict[str, Any]) -> bool:
        """Check if there are performance issues in metrics"""
        # Simple heuristics for performance issues
        aggregated = metrics.get('aggregated_metrics', {})
        
        # Check response time
        response_time = aggregated.get('avg_response_time', {})
        if response_time.get('latest', 0) > 1000:  # More than 1 second
            return True
        
        # Check error rate
        error_rate = aggregated.get('error_rate', {})
        if error_rate.get('latest', 0) > 0.05:  # More than 5% errors
            return True
        
        return False

    async def create_system_health_suggestion(self, health_status: Dict[str, Any]):
        """Create suggestion for system health issues"""
        # Implementation for system health suggestions
        pass

    async def create_performance_suggestion(self, metrics: Dict[str, Any]):
        """Create suggestion for performance issues"""
        # Implementation for performance suggestions
        pass

    async def get_suggestions(self, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all suggestions, optionally filtered by status"""
        suggestions = []
        
        for suggestion in self.actionable_suggestions.values():
            if status_filter is None or suggestion.status == status_filter:
                suggestions.append({
                    "id": suggestion.id,
                    "title": suggestion.title,
                    "description": suggestion.description,
                    "action_type": suggestion.action_type.value,
                    "priority": suggestion.priority,
                    "evidence": suggestion.evidence,
                    "implementation_plan": suggestion.implementation_plan,
                    "affected_files": suggestion.affected_files,
                    "estimated_effort": suggestion.estimated_effort,
                    "benefits": suggestion.benefits,
                    "risks": suggestion.risks,
                    "can_auto_apply": suggestion.can_auto_apply,
                    "created_at": suggestion.created_at.isoformat(),
                    "status": suggestion.status
                })
        
        # Sort by priority and creation time
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        suggestions.sort(key=lambda x: (priority_order.get(x["priority"], 4), x["created_at"]))
        
        return suggestions

    async def update_suggestion_status(self, suggestion_id: str, new_status: str) -> bool:
        """Update the status of a suggestion"""
        if suggestion_id in self.actionable_suggestions:
            self.actionable_suggestions[suggestion_id].status = new_status
            
            # Broadcast update
            suggestion = self.actionable_suggestions[suggestion_id]
            await self.broadcast_suggestion(suggestion)
            
            self.logger.info(f"Updated suggestion {suggestion_id} status to {new_status}")
            return True
        
        return False

    async def create_automatic_task(self, suggestion: ActionableSuggestion):
        """🎯 Sprint 9: Automatically create tasks from high-priority suggestions"""
        try:
            # Import AgentCoordinator here to avoid circular imports
            from src.orchestration.agent_coordinator import agent_coordinator
            
            # Create task description based on suggestion
            task_description = f"[AUTO] {suggestion.title}"
            
            # Determine agent type based on action type
            agent_type_mapping = {
                ActionType.REFACTOR: "ExecutionAgent",
                ActionType.FIX_CODE: "ExecutionAgent", 
                ActionType.SECURITY: "GuardianAgent",
                ActionType.DOCUMENT: "ExecutionAgent",
                ActionType.TEST: "ExecutionAgent",
                ActionType.OPTIMIZE: "ExecutionAgent",
                ActionType.CREATE_TASK: "ExecutionAgent"
            }
            
            agent_type = agent_type_mapping.get(suggestion.action_type, "ExecutionAgent")
            
            # Create task with detailed metadata
            task_metadata = {
                "suggestion_id": suggestion.id,
                "auto_generated": True,
                "implementation_plan": suggestion.implementation_plan,
                "affected_files": suggestion.affected_files,
                "estimated_effort": suggestion.estimated_effort,
                "evidence": suggestion.evidence,
                "benefits": suggestion.benefits,
                "risks": suggestion.risks,
                "can_auto_apply": suggestion.can_auto_apply
            }
            
            # Submit task to AgentCoordinator
            task_result = await agent_coordinator.create_and_submit_task(
                name=task_description,
                description=suggestion.description,
                agent_type=agent_type,
                priority=suggestion.priority,
                metadata=task_metadata
            )
            
            if task_result.get("success"):
                self.logger.info(f"🎯 Auto-created task {task_result.get('task_id')} for suggestion: {suggestion.title}")
                
                # Update suggestion status
                suggestion.status = "auto_task_created"
                
                # Broadcast task creation
                await self.broadcast_auto_task_created(suggestion, task_result)
                
                return task_result
            else:
                self.logger.error(f"Failed to auto-create task for suggestion {suggestion.id}: {task_result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error creating automatic task for suggestion {suggestion.id}: {e}")
        
        return None
    
    async def broadcast_auto_task_created(self, suggestion: ActionableSuggestion, task_result: dict):
        """Broadcast notification about auto-created task"""
        from src.api.websocket_manager import WebSocketMessage, MessageType
        
        message_data = {
            "suggestion_id": suggestion.id,
            "suggestion_title": suggestion.title,
            "task_id": task_result.get("task_id"),
            "task_name": task_result.get("name"),
            "priority": suggestion.priority,
            "agent_type": task_result.get("agent_type"),
            "created_at": datetime.now().isoformat(),
            "reason": f"Auto-created due to {suggestion.priority} priority" if suggestion.priority in ["high", "critical"] else "Auto-created because it can be auto-applied"
        }
        
        message = WebSocketMessage(
            message_type=MessageType.TASK_UPDATE,
            data=message_data,
            timestamp=datetime.now()
        )
        await self.websocket_manager.broadcast_message(message)

    async def broadcast_status(self, status):
        """Broadcast status update"""
        from src.api.websocket_manager import WebSocketMessage, MessageType
        
        status_data = {
            "status": status,
            "active_suggestions": len([s for s in self.actionable_suggestions.values() if s.status == "pending"]),
            "total_suggestions": len(self.actionable_suggestions),
            "last_analysis": self.last_full_analysis.isoformat() if self.last_full_analysis else None,
            "timestamp": datetime.now().isoformat()
        }
        
        message = WebSocketMessage(
            message_type=MessageType.AGENT_STATUS,
            data=status_data,
            timestamp=datetime.now()
        )
        await self.websocket_manager.broadcast_message(message)

    def stop(self):
        """Stop the Enhanced Supervisor Agent"""
        self.monitoring_active = False
        self.logger.info("Enhanced Supervisor Agent stopped")
