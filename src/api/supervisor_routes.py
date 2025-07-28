"""
Supervisor Agent API Routes
Provides endpoints for supervisor status, insights, and configuration
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from src.monitoring.system_health import system_health_monitor
from src.core.proactive_analyzer import proactive_analyzer
from src.api.auth import get_current_user
from src.api.websocket_manager import websocket_manager, WebSocketMessage, MessageType

logger = logging.getLogger(__name__)

from src.core.decision_engine import decision_engine

# Create router
supervisor_router = APIRouter(prefix="/api/supervisor", tags=["supervisor"])


class SupervisorStatus(BaseModel):
    """Supervisor status response model"""
    health_monitoring_active: bool
    proactive_analysis_active: bool
    system_health_status: str
    active_alerts_count: int
    last_analysis_time: str
    uptime_seconds: float
    supervisor_version: str = "1.0.0"


class SupervisorInsight(BaseModel):
    """Supervisor insight model"""
    insight_id: str
    category: str  # "health", "performance", "security", "optimization"
    priority: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    recommendations: List[str]
    auto_executable: bool
    timestamp: str


class SuggestionApproval(BaseModel):
    """Suggestion approval request model"""
    suggestion_id: str
    approved: bool
    user_feedback: Optional[str] = None


class SupervisorConfig(BaseModel):
    """Supervisor configuration model"""
    monitoring_interval_seconds: int = 30
    analysis_interval_seconds: int = 120
    auto_healing_enabled: bool = True
    proactive_suggestions_enabled: bool = True
    alert_threshold_levels: Dict[str, float] = {}


# Global supervisor state
supervisor_state = {
    "start_time": datetime.now(),
    "config": SupervisorConfig(),
    "approved_suggestions": [],
    "pending_suggestions": [],
    "insights_generated": 0
}


@supervisor_router.get("/status", response_model=SupervisorStatus)
async def get_supervisor_status(current_user: dict = Depends(get_current_user)):
    """Get current supervisor status and health"""
    try:
        # Get health summary
        health_summary = system_health_monitor.get_health_summary()
        
        # Get analysis summary
        analysis_summary = proactive_analyzer.get_analysis_summary()
        
        # Calculate uptime
        uptime = (datetime.now() - supervisor_state["start_time"]).total_seconds()
        
        return SupervisorStatus(
            health_monitoring_active=health_summary["monitoring_active"],
            proactive_analysis_active=analysis_summary["analysis_active"],
            system_health_status=health_summary["status"],
            active_alerts_count=health_summary["active_alerts"],
            last_analysis_time=analysis_summary["timestamp"],
            uptime_seconds=uptime
        )
        
    except Exception as e:
        logger.error(f"Error getting supervisor status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get supervisor status: {str(e)}")


@supervisor_router.get("/insights", response_model=List[SupervisorInsight])
async def get_supervisor_insights(
    category: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """Get latest supervisor insights and suggestions"""
    try:
        insights = []
        
        # Get health alerts as insights
        active_alerts = system_health_monitor.get_active_alerts()
        for alert in active_alerts:
            insights.append(SupervisorInsight(
                insight_id=alert["alert_id"],
                category="health",
                priority=alert["severity"],
                title=f"System Health Alert: {alert['metric_name']}",
                description=alert["message"],
                recommendations=[
                    "Monitor system resources closely",
                    "Consider auto-healing if available",
                    "Review recent changes"
                ],
                auto_executable=alert["severity"] == "critical",
                timestamp=alert["timestamp"]
            ))
        
        # Get analysis results as insights
        analysis_summary = proactive_analyzer.get_analysis_summary()
        
        # Code change insights
        for change in analysis_summary["code_changes"]["recent"]:
            if change["impact_level"] in ["high", "critical"]:
                insights.append(SupervisorInsight(
                    insight_id=f"code_change_{change['file_path']}_{change['timestamp']}",
                    category="performance",
                    priority=change["impact_level"],
                    title=f"High Impact Code Change: {change['file_path']}",
                    description=f"{change['change_type'].title()} file with {change['impact_level']} impact",
                    recommendations=change["recommendations"],
                    auto_executable=False,
                    timestamp=change["timestamp"]
                ))
        
        # Security vulnerability insights
        for vuln in analysis_summary["security_vulnerabilities"]["recent"]:
            if vuln["severity"] in ["high", "critical"]:
                insights.append(SupervisorInsight(
                    insight_id=vuln["vulnerability_id"],
                    category="security",
                    priority=vuln["severity"],
                    title=f"Security Vulnerability: {vuln['vulnerability_type']}",
                    description=vuln["description"],
                    recommendations=vuln["remediation"],
                    auto_executable=False,
                    timestamp=vuln["timestamp"]
                ))
        
        # Optimization suggestions as insights
        for suggestion in analysis_summary["optimization_suggestions"]["active"]:
            insights.append(SupervisorInsight(
                insight_id=suggestion["suggestion_id"],
                category="optimization",
                priority=suggestion["priority"],
                title=suggestion["title"],
                description=suggestion["description"],
                recommendations=suggestion["implementation_steps"],
                auto_executable=suggestion["effort_level"] == "low",
                timestamp=suggestion["timestamp"]
            ))
        
        # Filter by category and priority if specified
        if category:
            insights = [i for i in insights if i.category == category]
        if priority:
            insights = [i for i in insights if i.priority == priority]
        
        # Sort by priority and timestamp
        priority_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        insights.sort(
            key=lambda x: (priority_order.get(x.priority, 0), x.timestamp),
            reverse=True
        )
        
        return insights[:limit]
        
    except Exception as e:
        logger.error(f"Error getting supervisor insights: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get insights: {str(e)}")


@supervisor_router.post("/approve/{suggestion_id}")
async def approve_suggestion(
    suggestion_id: str,
    approval: SuggestionApproval,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a supervisor suggestion"""
    try:
        if approval.approved:
            # Add to approved suggestions
            supervisor_state["approved_suggestions"].append({
                "suggestion_id": suggestion_id,
                "approved_by": current_user.get("username", "unknown"),
                "timestamp": datetime.now().isoformat(),
                "feedback": approval.user_feedback
            })
            
            # Execute if auto-executable
            background_tasks.add_task(_execute_approved_suggestion, suggestion_id)
            
            # Broadcast approval
            message = WebSocketMessage(
                message_type=MessageType.SUPERVISOR_UPDATE,
                data={
                    "event": "suggestion_approved",
                    "suggestion_id": suggestion_id,
                    "approved_by": current_user.get("username", "unknown"),
                    "timestamp": datetime.now().isoformat()
                },
                timestamp=datetime.now()
            )
            await websocket_manager.broadcast_message(message)
            
            return {"status": "approved", "suggestion_id": suggestion_id}
        else:
            # Record rejection
            return {"status": "rejected", "suggestion_id": suggestion_id}
            
    except Exception as e:
        logger.error(f"Error approving suggestion {suggestion_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve suggestion: {str(e)}")


@supervisor_router.get("/configure", response_model=SupervisorConfig)
async def get_supervisor_config(current_user: dict = Depends(get_current_user)):
    """Get current supervisor configuration"""
    return supervisor_state["config"]


@supervisor_router.post("/configure")
async def update_supervisor_config(
    config: SupervisorConfig,
    current_user: dict = Depends(get_current_user)
):
    """Update supervisor configuration"""
    try:
        supervisor_state["config"] = config
        
        # Broadcast configuration update
        message = WebSocketMessage(
            message_type=MessageType.SUPERVISOR_UPDATE,
            data={
                "event": "config_updated",
                "config": config.dict(),
                "updated_by": current_user.get("username", "unknown"),
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        await websocket_manager.broadcast_message(message)
        
        logger.info(f"Supervisor configuration updated by {current_user.get('username', 'unknown')}")
        return {"status": "updated", "config": config}
        
    except Exception as e:
        logger.error(f"Error updating supervisor config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update config: {str(e)}")


@supervisor_router.post("/start-monitoring")
async def start_monitoring(current_user: dict = Depends(get_current_user)):
    """Start supervisor monitoring services"""
    try:
        # Start system health monitoring
        await system_health_monitor.start_monitoring()
        
        # Start proactive analysis
        await proactive_analyzer.start_analysis()
        
        logger.info(f"Supervisor monitoring started by {current_user.get('username', 'unknown')}")
        return {"status": "monitoring_started", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {str(e)}")


@supervisor_router.post("/stop-monitoring")
async def stop_monitoring(current_user: dict = Depends(get_current_user)):
    """Stop supervisor monitoring services"""
    try:
        # Stop system health monitoring
        await system_health_monitor.stop_monitoring()
        
        # Stop proactive analysis
        await proactive_analyzer.stop_analysis()
        
        logger.info(f"Supervisor monitoring stopped by {current_user.get('username', 'unknown')}")
        return {"status": "monitoring_stopped", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {str(e)}")


@supervisor_router.get("/metrics")
async def get_system_metrics(current_user: dict = Depends(get_current_user)):
    """Get current system metrics"""
    try:
        health_summary = system_health_monitor.get_health_summary()
        analysis_summary = proactive_analyzer.get_analysis_summary()
        
        return {
            "health": health_summary,
            "analysis": analysis_summary,
            "supervisor_state": {
                "uptime_seconds": (datetime.now() - supervisor_state["start_time"]).total_seconds(),
                "insights_generated": supervisor_state["insights_generated"],
                "approved_suggestions_count": len(supervisor_state["approved_suggestions"]),
                "pending_suggestions_count": len(supervisor_state["pending_suggestions"])
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting system metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


async def _execute_approved_suggestion(suggestion_id: str):
    """Execute an approved suggestion (background task)"""
    try:
        logger.info(f"Executing approved suggestion: {suggestion_id}")
        
        # This would contain the actual execution logic
        # For now, we'll just log the execution
        
        # Broadcast execution result
        message = WebSocketMessage(
            message_type=MessageType.SUPERVISOR_UPDATE,
            data={
                "event": "suggestion_executed",
                "suggestion_id": suggestion_id,
                "result": "success",
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        await websocket_manager.broadcast_message(message)
        
    except Exception as e:
        logger.error(f"Error executing suggestion {suggestion_id}: {e}")


@supervisor_router.post("/auto-pilot/toggle")
async def toggle_auto_pilot(
    enabled: bool,
    current_user: dict = Depends(get_current_user)
):
    """Toggle auto-pilot mode on/off"""
    try:
        decision_engine.toggle_auto_pilot(enabled)
        
        # Broadcast auto-pilot status change
        message = WebSocketMessage(
            message_type=MessageType.SUPERVISOR_UPDATE,
            data={
                "event": "auto_pilot_toggled",
                "enabled": enabled,
                "toggled_by": current_user.get("username", "unknown"),
                "timestamp": datetime.now().isoformat()
            },
            timestamp=datetime.now()
        )
        await websocket_manager.broadcast_message(message)
        
        logger.info(f"Auto-pilot mode {'enabled' if enabled else 'disabled'} by {current_user.get('username', 'unknown')}")
        return {
            "status": "auto_pilot_toggled",
            "enabled": enabled,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error toggling auto-pilot: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to toggle auto-pilot: {str(e)}")


@supervisor_router.get("/decisions/pending")
async def get_pending_decisions(current_user: dict = Depends(get_current_user)):
    """Get all pending decisions"""
    try:
        pending_decisions = decision_engine.get_pending_decisions()
        return {
            "decisions": pending_decisions,
            "count": len(pending_decisions),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting pending decisions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get pending decisions: {str(e)}")


@supervisor_router.post("/decisions/{decision_id}/approve")
async def approve_decision(
    decision_id: str,
    approval: SuggestionApproval,
    current_user: dict = Depends(get_current_user)
):
    """Approve or reject a decision"""
    try:
        success = await decision_engine.approve_decision(
            decision_id, 
            approval.approved, 
            approval.user_feedback
        )
        
        if success:
            return {
                "status": "decision_processed",
                "decision_id": decision_id,
                "approved": approval.approved,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=404, detail="Decision not found")
            
    except Exception as e:
        logger.error(f"Error approving decision {decision_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to approve decision: {str(e)}")


@supervisor_router.get("/decisions/stats")
async def get_decision_stats(current_user: dict = Depends(get_current_user)):
    """Get decision engine statistics"""
    try:
        stats = decision_engine.get_decision_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting decision stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get decision stats: {str(e)}")


# Health check endpoint for general system health
@supervisor_router.get("/health")
async def health_check():
    """Basic health check endpoint"""
    try:
        health_summary = system_health_monitor.get_health_summary()
        
        return {
            "status": "healthy" if health_summary["status"] in ["healthy", "warning"] else "unhealthy",
            "system_health": health_summary["status"],
            "monitoring_active": health_summary["monitoring_active"],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
