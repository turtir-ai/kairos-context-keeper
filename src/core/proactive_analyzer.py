"""
Proactive Analysis Engine for Kairos
Analyzes code changes, detects performance bottlenecks, scans for security vulnerabilities,
and provides resource usage optimization suggestions.
"""

import asyncio
import logging
import os
import ast
import re
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict, deque
import json
import hashlib
import subprocess

from src.monitoring.performance_tracker import performance_tracker
from src.monitoring.system_health import system_health_monitor


@dataclass
class CodeChangeImpact:
    """Code change impact analysis result"""
    file_path: str
    change_type: str  # "added", "modified", "deleted"
    impact_level: str  # "low", "medium", "high", "critical"
    affected_components: List[str]
    performance_impact: str
    security_impact: str
    recommendations: List[str]
    confidence: float
    timestamp: str


@dataclass
class PerformanceBottleneck:
    """Performance bottleneck detection result"""
    bottleneck_id: str
    component: str
    bottleneck_type: str  # "cpu", "memory", "io", "network", "database"
    severity: str  # "low", "medium", "high", "critical"
    current_metric: float
    expected_metric: float
    root_cause: str
    optimization_suggestions: List[str]
    estimated_improvement: str
    timestamp: str


@dataclass
class SecurityVulnerability:
    """Security vulnerability scan result"""
    vulnerability_id: str
    file_path: str
    line_number: int
    vulnerability_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    cwe_id: Optional[str]
    remediation: List[str]
    timestamp: str


@dataclass
class OptimizationSuggestion:
    """Resource optimization suggestion"""
    suggestion_id: str
    category: str  # "performance", "memory", "storage", "network"
    priority: str  # "low", "medium", "high", "critical"
    title: str
    description: str
    implementation_steps: List[str]
    expected_benefit: str
    effort_level: str  # "low", "medium", "high"
    timestamp: str


class ProactiveAnalyzer:
    """Proactive analysis engine for system optimization and security"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.analysis_active = False
        
        # Analysis results storage
        self.code_changes = deque(maxlen=100)
        self.bottlenecks = deque(maxlen=50)
        self.vulnerabilities = deque(maxlen=100)
        self.optimization_suggestions = deque(maxlen=50)
        
        # File monitoring
        self.file_hashes = {}
        self.monitored_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.json', '.yaml', '.yml'}
        
        # Performance patterns
        self.performance_patterns = {
            'slow_functions': [],
            'memory_leaks': [],
            'io_bottlenecks': [],
            'database_issues': []
        }
        
        # Security patterns to detect
        self.security_patterns = {
            'hardcoded_secrets': [
                r'(?i)(password|pwd|pass|secret|key|token|api)["\s]*[:=]["\s]*[a-zA-Z0-9+/=]{8,}',
                r'(?i)(sk_[a-zA-Z0-9]{20,}|Bearer\s+[a-zA-Z0-9+/=]{20,})',
                r'(?i)(AKIA[0-9A-Z]{16})'  # AWS Access Key
            ],
            'sql_injection': [
                r'(?i)(select|insert|update|delete).*?(from|into|set).*?[\'"][^\'"]*(\'|"|;)',
                r'(?i)execute\s*\(\s*[\'"][^\'"]*(\'|")\s*\+.*?\)',
            ],
            'xss_vulnerabilities': [
                r'(?i)innerHTML\s*=\s*[\'"][^\'"]*(\'|")\s*\+',
                r'(?i)document\.write\s*\(\s*[\'"][^\'"]*(\'|")\s*\+',
            ],
            'unsafe_file_operations': [
                r'(?i)open\s*\(\s*[\'"][^\'"]*(\'|")\s*\+.*?\)',
                r'(?i)exec\s*\(\s*[\'"][^\'"]*(\'|")\s*\+.*?\)',
            ]
        }
        
        self.logger.info("🔍 Proactive Analyzer initialized")
    
    async def start_analysis(self):
        """Start proactive analysis tasks"""
        if self.analysis_active:
            self.logger.warning("Proactive analysis is already active")
            return
        
        self.analysis_active = True
        self.logger.info("🚀 Starting proactive analysis")
        
        # Initialize file hashes for change detection
        await self._initialize_file_hashes()
        
        # Start analysis tasks
        asyncio.create_task(self._code_change_monitoring_loop())
        asyncio.create_task(self._performance_analysis_loop())
        asyncio.create_task(self._security_scan_loop())
        asyncio.create_task(self._optimization_analysis_loop())
        
        self.logger.info("✅ Proactive analysis started")
    
    async def stop_analysis(self):
        """Stop proactive analysis"""
        self.analysis_active = False
        self.logger.info("🛑 Proactive analysis stopped")
    
    async def _initialize_file_hashes(self):
        """Initialize file hashes for change detection"""
        try:
            project_root = Path(".")
            for file_path in project_root.rglob("*"):
                if file_path.is_file() and file_path.suffix in self.monitored_extensions:
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            file_hash = hashlib.md5(content).hexdigest()
                            self.file_hashes[str(file_path)] = file_hash
                    except Exception as e:
                        self.logger.debug(f"Could not hash {file_path}: {e}")
            
            self.logger.info(f"📝 Initialized hashes for {len(self.file_hashes)} files")
            
        except Exception as e:
            self.logger.error(f"Error initializing file hashes: {e}")
    
    async def _code_change_monitoring_loop(self):
        """Monitor code changes and analyze their impact"""
        while self.analysis_active:
            try:
                await self._detect_code_changes()
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                self.logger.error(f"Error in code change monitoring: {e}")
                await asyncio.sleep(60)
    
    async def _detect_code_changes(self):
        """Detect and analyze code changes"""
        try:
            project_root = Path(".")
            changes_detected = []
            
            for file_path in project_root.rglob("*"):
                if file_path.is_file() and file_path.suffix in self.monitored_extensions:
                    file_path_str = str(file_path)
                    
                    try:
                        with open(file_path, 'rb') as f:
                            content = f.read()
                            current_hash = hashlib.md5(content).hexdigest()
                        
                        old_hash = self.file_hashes.get(file_path_str)
                        
                        if old_hash is None:
                            # New file
                            change_type = "added"
                            self.file_hashes[file_path_str] = current_hash
                            changes_detected.append((file_path_str, change_type))
                            
                        elif old_hash != current_hash:
                            # Modified file
                            change_type = "modified"
                            self.file_hashes[file_path_str] = current_hash
                            changes_detected.append((file_path_str, change_type))
                    
                    except Exception as e:
                        self.logger.debug(f"Could not process {file_path}: {e}")
            
            # Check for deleted files
            existing_files = set(str(p) for p in project_root.rglob("*") 
                               if p.is_file() and p.suffix in self.monitored_extensions)
            for file_path_str in list(self.file_hashes.keys()):
                if file_path_str not in existing_files:
                    changes_detected.append((file_path_str, "deleted"))
                    del self.file_hashes[file_path_str]
            
            # Analyze detected changes
            for file_path, change_type in changes_detected:
                impact = await self._analyze_code_change_impact(file_path, change_type)
                if impact:
                    self.code_changes.append(impact)
                    
                    if impact.impact_level in ["high", "critical"]:
                        self.logger.warning(f"🚨 High impact code change detected: {file_path}")
                    
        except Exception as e:
            self.logger.error(f"Error detecting code changes: {e}")
    
    async def _analyze_code_change_impact(self, file_path: str, change_type: str) -> Optional[CodeChangeImpact]:
        """Analyze the impact of a code change"""
        try:
            # Determine impact level based on file type and location
            impact_level = self._calculate_impact_level(file_path, change_type)
            
            # Identify affected components
            affected_components = self._identify_affected_components(file_path)
            
            # Assess performance impact
            performance_impact = self._assess_performance_impact(file_path, change_type)
            
            # Assess security impact
            security_impact = await self._assess_security_impact(file_path, change_type)
            
            # Generate recommendations
            recommendations = self._generate_change_recommendations(file_path, change_type, impact_level)
            
            # Calculate confidence
            confidence = self._calculate_confidence(file_path, change_type)
            
            return CodeChangeImpact(
                file_path=file_path,
                change_type=change_type,
                impact_level=impact_level,
                affected_components=affected_components,
                performance_impact=performance_impact,
                security_impact=security_impact,
                recommendations=recommendations,
                confidence=confidence,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing code change impact for {file_path}: {e}")
            return None
    
    def _calculate_impact_level(self, file_path: str, change_type: str) -> str:
        """Calculate impact level based on file characteristics"""
        # Critical files
        critical_patterns = [
            r'.*/(main|daemon|server|app)\.py$',
            r'.*/config\.(py|json|yaml)$',
            r'.*/requirements\.txt$',
            r'.*/package\.json$'
        ]
        
        # High impact files
        high_patterns = [
            r'.*/agents/.*\.py$',
            r'.*/api/.*\.py$',
            r'.*/core/.*\.py$',
            r'.*/database/.*\.py$'
        ]
        
        # Medium impact files
        medium_patterns = [
            r'.*/monitoring/.*\.py$',
            r'.*/utils/.*\.py$',
            r'.*/tests/.*\.py$'
        ]
        
        for pattern in critical_patterns:
            if re.match(pattern, file_path):
                return "critical"
        
        for pattern in high_patterns:
            if re.match(pattern, file_path):
                return "high"
        
        for pattern in medium_patterns:
            if re.match(pattern, file_path):
                return "medium"
        
        return "low"
    
    def _identify_affected_components(self, file_path: str) -> List[str]:
        """Identify system components affected by the change"""
        components = []
        
        if "/agents/" in file_path:
            components.append("agent_system")
        if "/api/" in file_path:
            components.append("api_layer")
        if "/core/" in file_path:
            components.append("core_engine")
        if "/database/" in file_path or "/db/" in file_path:
            components.append("database")
        if "/monitoring/" in file_path:
            components.append("monitoring_system")
        if "/memory/" in file_path:
            components.append("memory_management")
        if "/mcp/" in file_path:
            components.append("mcp_integration")
        
        return components or ["general"]
    
    def _assess_performance_impact(self, file_path: str, change_type: str) -> str:
        """Assess potential performance impact"""
        if change_type == "deleted":
            return "neutral"
        
        # High performance impact patterns
        high_impact_patterns = [
            r'.*/(memory|cache|db|database).*\.py$',
            r'.*/performance.*\.py$',
            r'.*/monitoring.*\.py$'
        ]
        
        for pattern in high_impact_patterns:
            if re.match(pattern, file_path):
                return "high"
        
        if "/core/" in file_path or "/agents/" in file_path:
            return "medium"
        
        return "low"
    
    async def _assess_security_impact(self, file_path: str, change_type: str) -> str:
        """Assess potential security impact"""
        if change_type == "deleted":
            return "neutral"
        
        try:
            # Check if file contains security-sensitive patterns
            if not Path(file_path).exists():
                return "neutral"
            
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Check for security patterns
            for pattern_type, patterns in self.security_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, content):
                        return "high"
            
            # Security-sensitive file patterns
            security_patterns = [
                r'.*/auth.*\.py$',
                r'.*/security.*\.py$',
                r'.*/crypto.*\.py$',
                r'.*/(api|auth)_.*\.py$'
            ]
            
            for pattern in security_patterns:
                if re.match(pattern, file_path):
                    return "medium"
            
            return "low"
            
        except Exception as e:
            self.logger.debug(f"Error assessing security impact for {file_path}: {e}")
            return "unknown"
    
    def _generate_change_recommendations(self, file_path: str, change_type: str, impact_level: str) -> List[str]:
        """Generate recommendations for code changes"""
        recommendations = []
        
        if impact_level in ["high", "critical"]:
            recommendations.extend([
                "Run comprehensive tests before deployment",
                "Monitor system performance after deployment",
                "Consider staged rollout for this change"
            ])
        
        if "/api/" in file_path:
            recommendations.append("Verify API endpoint functionality and documentation")
            
        if "/database/" in file_path or "/db/" in file_path:
            recommendations.extend([
                "Run database migration tests",
                "Backup database before deployment"
            ])
        
        if "/agents/" in file_path:
            recommendations.append("Test agent coordination and task execution")
        
        if change_type == "added":
            recommendations.append("Review new code for security vulnerabilities")
        elif change_type == "modified":
            recommendations.append("Compare performance before and after changes")
        elif change_type == "deleted":
            recommendations.append("Verify no dependencies on deleted code")
        
        return recommendations
    
    def _calculate_confidence(self, file_path: str, change_type: str) -> float:
        """Calculate confidence in impact analysis"""
        confidence = 0.5  # Base confidence
        
        # Higher confidence for known patterns
        if any(pattern in file_path for pattern in ["/agents/", "/api/", "/core/"]):
            confidence += 0.3
        
        # File type confidence
        if file_path.endswith('.py'):
            confidence += 0.2
        elif file_path.endswith(('.json', '.yaml', '.yml')):
            confidence += 0.1
        
        return min(1.0, confidence)
    
    async def _performance_analysis_loop(self):
        """Analyze performance bottlenecks"""
        while self.analysis_active:
            try:
                await self._detect_performance_bottlenecks()
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                self.logger.error(f"Error in performance analysis: {e}")
                await asyncio.sleep(300)
    
    async def _detect_performance_bottlenecks(self):
        """Detect performance bottlenecks in the system"""
        try:
            # Get current performance metrics
            perf_metrics = performance_tracker.get_metrics_summary(time_range_minutes=10)
            health_metrics = system_health_monitor.current_metrics
            
            # Analyze CPU bottlenecks
            if health_metrics.get("cpu_percent", 0) > 80:
                bottleneck = PerformanceBottleneck(
                    bottleneck_id=f"cpu_bottleneck_{int(time.time())}",
                    component="system_cpu",
                    bottleneck_type="cpu",
                    severity="high" if health_metrics["cpu_percent"] > 90 else "medium",
                    current_metric=health_metrics["cpu_percent"],
                    expected_metric=50.0,
                    root_cause="High CPU utilization detected",
                    optimization_suggestions=[
                        "Identify CPU-intensive processes",
                        "Optimize algorithm efficiency",
                        "Consider task scheduling optimization"
                    ],
                    estimated_improvement="20-40% CPU reduction",
                    timestamp=datetime.now().isoformat()
                )
                self.bottlenecks.append(bottleneck)
            
            # Analyze memory bottlenecks
            if health_metrics.get("memory_percent", 0) > 85:
                bottleneck = PerformanceBottleneck(
                    bottleneck_id=f"memory_bottleneck_{int(time.time())}",
                    component="system_memory",
                    bottleneck_type="memory",
                    severity="high" if health_metrics["memory_percent"] > 95 else "medium",
                    current_metric=health_metrics["memory_percent"],
                    expected_metric=70.0,
                    root_cause="High memory utilization detected",
                    optimization_suggestions=[
                        "Implement memory cleanup routines",
                        "Optimize data structures",
                        "Add memory monitoring and alerting"
                    ],
                    estimated_improvement="15-30% memory reduction",
                    timestamp=datetime.now().isoformat()
                )
                self.bottlenecks.append(bottleneck)
            
            # Analyze response time bottlenecks
            avg_response_time = health_metrics.get("avg_response_time_ms", 0)
            if avg_response_time > 2000:
                bottleneck = PerformanceBottleneck(
                    bottleneck_id=f"response_bottleneck_{int(time.time())}",
                    component="api_layer",
                    bottleneck_type="io",
                    severity="high" if avg_response_time > 5000 else "medium",
                    current_metric=avg_response_time,
                    expected_metric=500.0,
                    root_cause="Slow API response times detected",
                    optimization_suggestions=[
                        "Implement response caching",
                        "Optimize database queries",
                        "Use faster model endpoints"
                    ],
                    estimated_improvement="50-70% faster responses",
                    timestamp=datetime.now().isoformat()
                )
                self.bottlenecks.append(bottleneck)
            
        except Exception as e:
            self.logger.error(f"Error detecting performance bottlenecks: {e}")
    
    async def _security_scan_loop(self):
        """Perform security vulnerability scans"""
        while self.analysis_active:
            try:
                await self._scan_security_vulnerabilities()
                await asyncio.sleep(600)  # Check every 10 minutes
                
            except Exception as e:
                self.logger.error(f"Error in security scan: {e}")
                await asyncio.sleep(600)
    
    async def _scan_security_vulnerabilities(self):
        """Scan for security vulnerabilities in code"""
        try:
            project_root = Path(".")
            
            for file_path in project_root.rglob("*.py"):
                if file_path.is_file():
                    await self._scan_file_for_vulnerabilities(str(file_path))
                    
        except Exception as e:
            self.logger.error(f"Error scanning security vulnerabilities: {e}")
    
    async def _scan_file_for_vulnerabilities(self, file_path: str):
        """Scan a single file for security vulnerabilities"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            for pattern_type, patterns in self.security_patterns.items():
                for pattern in patterns:
                    for line_num, line in enumerate(lines, 1):
                        if re.search(pattern, line):
                            vulnerability = SecurityVulnerability(
                                vulnerability_id=f"{pattern_type}_{file_path}_{line_num}_{int(time.time())}",
                                file_path=file_path,
                                line_number=line_num,
                                vulnerability_type=pattern_type,
                                severity=self._determine_vulnerability_severity(pattern_type),
                                description=f"{pattern_type.replace('_', ' ').title()} detected in {file_path}:{line_num}",
                                cwe_id=self._get_cwe_id(pattern_type),
                                remediation=self._get_remediation_steps(pattern_type),
                                timestamp=datetime.now().isoformat()
                            )
                            
                            self.vulnerabilities.append(vulnerability)
                            
                            if vulnerability.severity in ["high", "critical"]:
                                self.logger.warning(f"🚨 Security vulnerability detected: {vulnerability.description}")
            
        except Exception as e:
            self.logger.debug(f"Error scanning {file_path}: {e}")
    
    def _determine_vulnerability_severity(self, vuln_type: str) -> str:
        """Determine severity of vulnerability based on type"""
        severity_map = {
            'hardcoded_secrets': 'critical',
            'sql_injection': 'high',
            'xss_vulnerabilities': 'high',
            'unsafe_file_operations': 'medium'
        }
        return severity_map.get(vuln_type, 'medium')
    
    def _get_cwe_id(self, vuln_type: str) -> Optional[str]:
        """Get CWE ID for vulnerability type"""
        cwe_map = {
            'hardcoded_secrets': 'CWE-798',
            'sql_injection': 'CWE-89',
            'xss_vulnerabilities': 'CWE-79',
            'unsafe_file_operations': 'CWE-73'
        }
        return cwe_map.get(vuln_type)
    
    def _get_remediation_steps(self, vuln_type: str) -> List[str]:
        """Get remediation steps for vulnerability type"""
        remediation_map = {
            'hardcoded_secrets': [
                "Move secrets to environment variables",
                "Use a secrets management system",
                "Remove hardcoded credentials from code"
            ],
            'sql_injection': [
                "Use parameterized queries",
                "Validate and sanitize user input",
                "Use ORM with built-in protections"
            ],
            'xss_vulnerabilities': [
                "Sanitize user input before rendering",
                "Use proper encoding for output",
                "Implement Content Security Policy"
            ],
            'unsafe_file_operations': [
                "Validate file paths and names",
                "Use secure file operation libraries",
                "Implement proper access controls"
            ]
        }
        return remediation_map.get(vuln_type, ["Review and secure the code"])
    
    async def _optimization_analysis_loop(self):
        """Generate optimization suggestions"""
        while self.analysis_active:
            try:
                await self._generate_optimization_suggestions()
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Error in optimization analysis: {e}")
                await asyncio.sleep(300)
    
    async def _generate_optimization_suggestions(self):
        """Generate resource optimization suggestions"""
        try:
            # Get current system state
            health_metrics = system_health_monitor.current_metrics
            perf_metrics = performance_tracker.get_metrics_summary(time_range_minutes=15)
            
            suggestions = []
            
            # Memory optimization suggestions
            memory_percent = health_metrics.get("memory_percent", 0)
            if memory_percent > 70:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"memory_opt_{int(time.time())}",
                    category="memory",
                    priority="high" if memory_percent > 85 else "medium",
                    title="Memory Usage Optimization",
                    description=f"Current memory usage is {memory_percent:.1f}%. Consider optimizing memory usage.",
                    implementation_steps=[
                        "Implement periodic garbage collection",
                        "Optimize data structure usage",
                        "Add memory monitoring and alerting",
                        "Consider memory-efficient algorithms"
                    ],
                    expected_benefit=f"Reduce memory usage by 15-25%",
                    effort_level="medium",
                    timestamp=datetime.now().isoformat()
                ))
            
            # Performance optimization suggestions
            avg_response_time = health_metrics.get("avg_response_time_ms", 0)
            if avg_response_time > 1000:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"perf_opt_{int(time.time())}",
                    category="performance",
                    priority="high" if avg_response_time > 3000 else "medium",
                    title="API Response Time Optimization",
                    description=f"Average response time is {avg_response_time:.0f}ms. Consider optimization.",
                    implementation_steps=[
                        "Implement response caching",
                        "Optimize database queries",
                        "Use connection pooling",
                        "Consider async processing for heavy operations"
                    ],
                    expected_benefit="Reduce response time by 40-60%",
                    effort_level="medium",
                    timestamp=datetime.now().isoformat()
                ))
            
            # Storage optimization suggestions
            disk_usage = health_metrics.get("disk_usage_percent", 0)
            if disk_usage > 80:
                suggestions.append(OptimizationSuggestion(
                    suggestion_id=f"storage_opt_{int(time.time())}",
                    category="storage",
                    priority="high" if disk_usage > 90 else "medium",
                    title="Disk Space Optimization",
                    description=f"Disk usage is {disk_usage:.1f}%. Consider cleanup and optimization.",
                    implementation_steps=[
                        "Implement log rotation",
                        "Clean up old temporary files",
                        "Compress old data archives",
                        "Implement data retention policies"
                    ],
                    expected_benefit="Free up 20-40% disk space",
                    effort_level="low",
                    timestamp=datetime.now().isoformat()
                ))
            
            # Add suggestions to queue
            for suggestion in suggestions:
                self.optimization_suggestions.append(suggestion)
                
                if suggestion.priority == "high":
                    self.logger.info(f"💡 High priority optimization suggestion: {suggestion.title}")
            
        except Exception as e:
            self.logger.error(f"Error generating optimization suggestions: {e}")
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        return {
            "analysis_active": self.analysis_active,
            "code_changes": {
                "total": len(self.code_changes),
                "recent": [asdict(change) for change in list(self.code_changes)[-5:]]
            },
            "performance_bottlenecks": {
                "total": len(self.bottlenecks),
                "active": [asdict(bottleneck) for bottleneck in self.bottlenecks]
            },
            "security_vulnerabilities": {
                "total": len(self.vulnerabilities),
                "critical": len([v for v in self.vulnerabilities if v.severity == "critical"]),
                "high": len([v for v in self.vulnerabilities if v.severity == "high"]),
                "recent": [asdict(vuln) for vuln in list(self.vulnerabilities)[-5:]]
            },
            "optimization_suggestions": {
                "total": len(self.optimization_suggestions),
                "high_priority": len([o for o in self.optimization_suggestions if o.priority == "high"]),
                "active": [asdict(suggestion) for suggestion in self.optimization_suggestions]
            },
            "timestamp": datetime.now().isoformat()
        }


# Global instance
proactive_analyzer = ProactiveAnalyzer()
