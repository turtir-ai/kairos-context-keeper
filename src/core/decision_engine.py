"""
Decision Engine for Supervisor Agent
Handles decision-making, user feedback learning, and auto-pilot mode functionality
"""

import asyncio
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from pathlib import Path

from src.monitoring.system_health import system_health_monitor
from src.core.proactive_analyzer import proactive_analyzer
from src.api.websocket_manager import websocket_manager, WebSocketMessage, MessageType

logger = logging.getLogger(__name__)


@dataclass
class Decision:
    """Decision data structure"""
    decision_id: str
    category: str  # "suggestion", "alert", "optimization", "security"
    description: str
    confidence: float
    reasoning: List[str]
    auto_executable: bool
    user_feedback: Optional[str] = None
    approved: Optional[bool] = None
    executed: bool = False
    timestamp: str = ""


@dataclass
class LearningRecord:
    """User feedback learning record"""
    record_id: str
    decision_type: str
    context: Dict[str, Any]
    user_action: str  # "approved", "rejected", "modified"
    feedback: Optional[str]
    outcome: Optional[str]
    timestamp: str


class DecisionEngine:
    """Decision engine with user feedback learning and auto-pilot mode"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.decisions_queue = deque(maxlen=100)
        self.learning_records = deque(maxlen=500)
        self.auto_pilot_enabled = False
        self.confidence_threshold = 0.8
        
        # Decision patterns learned from user feedback
        self.learned_patterns = {
            "approval_patterns": defaultdict(list),
            "rejection_patterns": defaultdict(list),
            "modification_patterns": defaultdict(list)
        }
        
        # Task templates for auto-creation
        self.task_templates = {
            "performance_optimization": {
                "title": "Performance Optimization Required",
                "description": "System performance degradation detected. Optimization needed.",
                "agent": "ExecutionAgent",
                "priority": "high",
                "auto_executable": True
            },
            "security_vulnerability": {
                "title": "Security Vulnerability Found",
                "description": "Security vulnerability detected in codebase. Immediate attention required.",
                "agent": "GuardianAgent", 
                "priority": "critical",
                "auto_executable": False
            },
            "code_quality_review": {
                "title": "Code Quality Review",
                "description": "Recent code changes require quality review and optimization.",
                "agent": "RetrievalAgent",
                "priority": "medium",
                "auto_executable": True
            },
            "system_health_check": {
                "title": "System Health Check",
                "description": "Periodic system health verification and maintenance.",
                "agent": "GuardianAgent",
                "priority": "low",
                "auto_executable": True
            }
        }
        
        self.logger.info("🧠 Decision Engine initialized")
    
    async def start_decision_processing(self):
        """Start the decision processing loop"""
        asyncio.create_task(self._decision_processing_loop())
        asyncio.create_task(self._auto_pilot_loop())
        self.logger.info("🚀 Decision processing started")
    
    async def _decision_processing_loop(self):
        """Main decision processing loop"""
        while True:
            try:
                await self._analyze_system_state()
                await self._generate_proactive_decisions()
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Error in decision processing loop: {e}")
                await asyncio.sleep(60)
    
    async def _auto_pilot_loop(self):
        """Auto-pilot mode execution loop"""
        while True:
            try:
                if self.auto_pilot_enabled:
                    await self._execute_auto_pilot_decisions()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in auto-pilot loop: {e}")
                await asyncio.sleep(30)
    
    async def _analyze_system_state(self):
        """Analyze current system state and generate decisions"""
        try:
            # Get current system health
            health_summary = system_health_monitor.get_health_summary()
            analysis_summary = proactive_analyzer.get_analysis_summary()
            
            # Generate decisions based on health alerts
            if health_summary["active_alerts"] > 0:
                alerts = system_health_monitor.get_active_alerts()
                for alert in alerts:
                    await self._create_decision_from_alert(alert)
            
            # Generate decisions based on analysis results
            await self._create_decisions_from_analysis(analysis_summary)
            
        except Exception as e:
            self.logger.error(f"Error analyzing system state: {e}")
    
    async def _create_decision_from_alert(self, alert: Dict[str, Any]):
        """Create a decision from a system alert"""
        try:
            decision = Decision(
                decision_id=f"alert_decision_{alert['alert_id']}_{int(time.time())}",
                category="alert",
                description=f"System alert requires attention: {alert['message']}",
                confidence=0.9 if alert["severity"] in ["critical", "high"] else 0.7,
                reasoning=[
                    f"Alert severity: {alert['severity']}",
                    f"Metric: {alert['metric_name']}",
                    f"Current value: {alert['current_value']}",
                    f"Threshold: {alert['threshold']}"
                ],
                auto_executable=alert["severity"] == "critical",
                timestamp=datetime.now().isoformat()
            )
            
            await self._add_decision(decision)
            
        except Exception as e:
            self.logger.error(f"Error creating decision from alert: {e}")
    
    async def _create_decisions_from_analysis(self, analysis: Dict[str, Any]):
        """Create decisions from proactive analysis results"""
        try:
            # Security vulnerability decisions
            for vuln in analysis["security_vulnerabilities"]["recent"]:
                if vuln["severity"] in ["high", "critical"]:
                    decision = Decision(
                        decision_id=f"security_decision_{vuln['vulnerability_id']}",
                        category="security",
                        description=f"Security vulnerability detected: {vuln['description']}",
                        confidence=0.95 if vuln["severity"] == "critical" else 0.8,
                        reasoning=[
                            f"Vulnerability type: {vuln['vulnerability_type']}",
                            f"Severity: {vuln['severity']}",
                            f"File: {vuln['file_path']}:{vuln['line_number']}",
                            f"CWE ID: {vuln.get('cwe_id', 'Unknown')}"
                        ],
                        auto_executable=False,  # Security issues need manual review
                        timestamp=datetime.now().isoformat()
                    )
                    await self._add_decision(decision)
            
            # Performance optimization decisions
            for suggestion in analysis["optimization_suggestions"]["active"]:
                if suggestion["priority"] in ["high", "critical"]:
                    decision = Decision(
                        decision_id=f"optimization_decision_{suggestion['suggestion_id']}",
                        category="optimization",
                        description=suggestion["description"],
                        confidence=0.8,
                        reasoning=[
                            f"Category: {suggestion['category']}",
                            f"Priority: {suggestion['priority']}",
                            f"Expected benefit: {suggestion['expected_benefit']}",
                            f"Effort level: {suggestion['effort_level']}"
                        ],
                        auto_executable=suggestion["effort_level"] == "low",
                        timestamp=datetime.now().isoformat()
                    )
                    await self._add_decision(decision)
            
        except Exception as e:
            self.logger.error(f"Error creating decisions from analysis: {e}")
    
    async def _generate_proactive_decisions(self):
        """Generate proactive decisions based on learned patterns"""
        try:
            # Check if it's time for routine tasks
            current_hour = datetime.now().hour
            
            # Morning health check (9 AM)
            if current_hour == 9 and await self._should_create_routine_task("morning_health_check"):
                await self._create_routine_task("system_health_check", "Morning system health verification")
            
            # Afternoon performance review (2 PM)  
            if current_hour == 14 and await self._should_create_routine_task("afternoon_performance"):
                await self._create_routine_task("performance_optimization", "Afternoon performance optimization review")
            
            # Evening security scan (6 PM)
            if current_hour == 18 and await self._should_create_routine_task("evening_security"):
                await self._create_routine_task("security_vulnerability", "Evening security vulnerability scan")
            
        except Exception as e:
            self.logger.error(f"Error generating proactive decisions: {e}")
    
    async def _should_create_routine_task(self, routine_type: str) -> bool:
        """Check if a routine task should be created based on patterns"""
        # Simple check: don't create if similar task was created in last 2 hours
        cutoff_time = datetime.now() - timedelta(hours=2)
        
        for decision in self.decisions_queue:
            if (decision.category == routine_type and 
                datetime.fromisoformat(decision.timestamp.replace('Z', '+00:00')) > cutoff_time):
                return False
        
        return True
    
    async def _create_routine_task(self, task_type: str, custom_description: str = None):
        """Create a routine task based on template"""
        try:
            template = self.task_templates.get(task_type)
            if not template:
                return
            
            decision = Decision(
                decision_id=f"routine_{task_type}_{int(time.time())}",
                category="routine",
                description=custom_description or template["description"],
                confidence=0.7,
                reasoning=[
                    "Routine maintenance task",
                    f"Task type: {task_type}",
                    f"Scheduled execution based on patterns"
                ],
                auto_executable=template["auto_executable"],
                timestamp=datetime.now().isoformat()
            )
            
            await self._add_decision(decision)
            
        except Exception as e:
            self.logger.error(f"Error creating routine task: {e}")
    
    async def _add_decision(self, decision: Decision):
        """Add a decision to the queue and broadcast it"""
        try:
            self.decisions_queue.append(decision)
            
            # Broadcast decision to frontend
            message = WebSocketMessage(
                message_type=MessageType.SUPERVISOR_UPDATE,
                data={
                    "event": "new_decision",
                    "decision": asdict(decision),
                    "timestamp": datetime.now().isoformat()
                },
                timestamp=datetime.now()
            )
            await websocket_manager.broadcast_message(message)
            
            self.logger.info(f"🎯 New decision created: {decision.description}")
            
        except Exception as e:
            self.logger.error(f"Error adding decision: {e}")
    
    async def _execute_auto_pilot_decisions(self):
        """Execute decisions automatically in auto-pilot mode"""
        try:
            for decision in list(self.decisions_queue):
                if (decision.auto_executable and 
                    not decision.executed and 
                    decision.confidence >= self.confidence_threshold):
                    
                    # Execute the decision
                    success = await self._execute_decision(decision)
                    
                    if success:
                        decision.executed = True
                        decision.approved = True
                        
                        # Broadcast execution
                        message = WebSocketMessage(
                            message_type=MessageType.SUPERVISOR_UPDATE,
                            data={
                                "event": "decision_executed",
                                "decision_id": decision.decision_id,
                                "result": "success",
                                "timestamp": datetime.now().isoformat()
                            },
                            timestamp=datetime.now()
                        )
                        await websocket_manager.broadcast_message(message)
                        
                        self.logger.info(f"🤖 Auto-pilot executed: {decision.description}")
                    
        except Exception as e:
            self.logger.error(f"Error in auto-pilot execution: {e}")
    
    async def _execute_decision(self, decision: Decision) -> bool:
        """Execute a specific decision"""
        try:
            # This would contain the actual execution logic
            # For now, we'll simulate execution
            
            await asyncio.sleep(1)  # Simulate processing time
            
            # Create a task based on the decision
            task_data = {
                "type": decision.category,
                "description": decision.description,
                "priority": "high" if decision.confidence > 0.8 else "medium",
                "agent": self._determine_agent_for_decision(decision),
                "auto_created": True,
                "decision_id": decision.decision_id
            }
            
            # Here you would integrate with task creation system
            # await task_orchestrator.create_task(task_data)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error executing decision {decision.decision_id}: {e}")
            return False
    
    def _determine_agent_for_decision(self, decision: Decision) -> str:
        """Determine which agent should handle the decision"""
        if decision.category == "security":
            return "GuardianAgent"
        elif decision.category in ["optimization", "performance"]:
            return "ExecutionAgent"
        elif decision.category == "alert":
            return "GuardianAgent"
        else:
            return "RetrievalAgent"
    
    async def approve_decision(self, decision_id: str, approved: bool, feedback: str = None) -> bool:
        """Process user approval/rejection of a decision"""
        try:
            # Find the decision
            decision = None
            for d in self.decisions_queue:
                if d.decision_id == decision_id:
                    decision = d
                    break
            
            if not decision:
                self.logger.error(f"Decision not found: {decision_id}")
                return False
            
            # Update decision
            decision.approved = approved
            decision.user_feedback = feedback
            
            # Record learning data
            learning_record = LearningRecord(
                record_id=f"learning_{decision_id}_{int(time.time())}",
                decision_type=decision.category,
                context={
                    "confidence": decision.confidence,
                    "auto_executable": decision.auto_executable,
                    "reasoning": decision.reasoning
                },
                user_action="approved" if approved else "rejected",
                feedback=feedback,
                outcome=None,  # Will be updated later
                timestamp=datetime.now().isoformat()
            )
            
            self.learning_records.append(learning_record)
            
            # Update learned patterns
            await self._update_learned_patterns(learning_record)
            
            # Execute if approved
            if approved:
                success = await self._execute_decision(decision)
                decision.executed = success
                learning_record.outcome = "success" if success else "failed"
            
            self.logger.info(f"📝 Decision {decision_id} {'approved' if approved else 'rejected'}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error processing decision approval: {e}")
            return False
    
    async def _update_learned_patterns(self, record: LearningRecord):
        """Update learned patterns based on user feedback"""
        try:
            pattern_key = record.decision_type
            
            if record.user_action == "approved":
                self.learned_patterns["approval_patterns"][pattern_key].append({
                    "context": record.context,
                    "feedback": record.feedback,
                    "timestamp": record.timestamp
                })
            elif record.user_action == "rejected":
                self.learned_patterns["rejection_patterns"][pattern_key].append({
                    "context": record.context,
                    "feedback": record.feedback,
                    "timestamp": record.timestamp
                })
            
            # Adjust confidence thresholds based on patterns
            await self._adjust_confidence_thresholds()
            
        except Exception as e:
            self.logger.error(f"Error updating learned patterns: {e}")
    
    async def _adjust_confidence_thresholds(self):
        """Adjust confidence thresholds based on learned patterns"""
        try:
            # Simple learning: if most high-confidence decisions are approved,
            # we can be more aggressive in auto-pilot mode
            
            recent_records = [r for r in self.learning_records 
                            if datetime.fromisoformat(r.timestamp.replace('Z', '+00:00')) > 
                               datetime.now() - timedelta(days=7)]
            
            if len(recent_records) > 10:
                high_confidence_approvals = sum(1 for r in recent_records 
                                              if r.context.get("confidence", 0) > 0.8 and 
                                                 r.user_action == "approved")
                
                high_confidence_total = sum(1 for r in recent_records 
                                          if r.context.get("confidence", 0) > 0.8)
                
                if high_confidence_total > 0:
                    approval_rate = high_confidence_approvals / high_confidence_total
                    
                    # Adjust threshold based on approval rate
                    if approval_rate > 0.9:
                        self.confidence_threshold = max(0.7, self.confidence_threshold - 0.05)
                    elif approval_rate < 0.6:
                        self.confidence_threshold = min(0.95, self.confidence_threshold + 0.05)
                    
                    self.logger.info(f"🎯 Confidence threshold adjusted to {self.confidence_threshold:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error adjusting confidence thresholds: {e}")
    
    def toggle_auto_pilot(self, enabled: bool):
        """Toggle auto-pilot mode"""
        self.auto_pilot_enabled = enabled
        self.logger.info(f"🤖 Auto-pilot mode {'enabled' if enabled else 'disabled'}")
    
    def get_pending_decisions(self) -> List[Dict[str, Any]]:
        """Get all pending decisions"""
        return [asdict(d) for d in self.decisions_queue if not d.executed and d.approved is None]
    
    def get_decision_stats(self) -> Dict[str, Any]:
        """Get decision engine statistics"""
        total_decisions = len(self.decisions_queue)
        approved = sum(1 for d in self.decisions_queue if d.approved is True)
        rejected = sum(1 for d in self.decisions_queue if d.approved is False)
        executed = sum(1 for d in self.decisions_queue if d.executed)
        
        return {
            "total_decisions": total_decisions,
            "approved": approved,
            "rejected": rejected,
            "executed": executed,
            "pending": total_decisions - approved - rejected,
            "auto_pilot_enabled": self.auto_pilot_enabled,
            "confidence_threshold": self.confidence_threshold,
            "learning_records": len(self.learning_records),
            "timestamp": datetime.now().isoformat()
        }


# Global instance
decision_engine = DecisionEngine()
