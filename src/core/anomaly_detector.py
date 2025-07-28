"""
Anomaly Detection System for Kairos
Monitors system metrics and detects performance anomalies, unusual patterns, and potential issues.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from collections import deque, defaultdict
import json
import math
import statistics
import asyncpg
import redis.asyncio as redis
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats

@dataclass
class AnomalyAlert:
    """Represents an anomaly detection alert"""
    alert_id: str
    alert_type: str  # 'performance', 'cost', 'usage', 'error_rate'
    severity: str    # 'low', 'medium', 'high', 'critical'
    metric_name: str
    current_value: float
    expected_range: Tuple[float, float]
    deviation_score: float
    confidence: float
    description: str
    affected_components: List[str]
    suggested_actions: List[str]
    detected_at: str
    resolved_at: Optional[str] = None
    resolved: bool = False

@dataclass
class MetricBaseline:
    """Baseline metrics for anomaly detection"""
    metric_name: str
    mean: float
    std_dev: float
    min_value: float
    max_value: float
    percentile_95: float
    percentile_99: float
    sample_count: int
    last_updated: str

class AnomalyDetector:
    """Advanced anomaly detection system with ML-based monitoring"""
    
    def __init__(self, db_pool=None, redis_client=None):
        self.logger = logging.getLogger(__name__)
        self.db_pool = db_pool
        self.redis_client = redis_client
        
        # Detection parameters
        self.baseline_window_days = 7    # Days of data for baseline calculation
        self.detection_threshold = 2.5   # Standard deviations for anomaly detection
        self.confidence_threshold = 0.8  # Minimum confidence for alerts
        self.max_alerts_per_hour = 5     # Rate limiting for alerts
        
        # Metric storage and processing
        self.metric_history = defaultdict(lambda: deque(maxlen=1000))
        self.baselines = {}
        self.active_alerts = {}
        self.alert_history = deque(maxlen=100)
        
        # ML models for anomaly detection
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.model_trained = False
        
        # Monitoring rules and thresholds
        self.monitoring_rules = {
            'response_time_ms': {
                'threshold_multiplier': 3.0,
                'min_samples': 10,
                'severity_levels': {'high': 5000, 'critical': 10000}
            },
            'error_rate': {
                'threshold_multiplier': 2.0,
                'min_samples': 5,
                'severity_levels': {'medium': 0.05, 'high': 0.15, 'critical': 0.3}
            },
            'cpu_percent': {
                'threshold_multiplier': 2.0,
                'min_samples': 5,
                'severity_levels': {'medium': 70, 'high': 85, 'critical': 95}
            },
            'memory_percent': {
                'threshold_multiplier': 2.0,
                'min_samples': 5,
                'severity_levels': {'medium': 75, 'high': 90, 'critical': 95}
            },
            'api_cost_usd': {
                'threshold_multiplier': 4.0,
                'min_samples': 3,
                'severity_levels': {'medium': 10, 'high': 50, 'critical': 100}
            }
        }
        
        self.logger.info("🚨 Anomaly Detector initialized")
    
    async def initialize(self):
        """Initialize the anomaly detector with historical data"""
        if not self.db_pool:
            self.logger.warning("Anomaly detector initialized without database connection")
            return
        
        await self._create_anomaly_tables()
        await self._load_existing_baselines()
        await self._calculate_baselines()
        await self._train_ml_models()
        
        # Start background monitoring
        asyncio.create_task(self._background_monitoring())
        
        self.logger.info("✅ Anomaly detector initialized with historical baselines")
    
    async def _create_anomaly_tables(self):
        """Create anomaly detection tables"""
        try:
            async with self.db_pool.acquire() as conn:
                # Metric baselines table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS metric_baselines (
                        metric_name VARCHAR(255) PRIMARY KEY,
                        mean_value DECIMAL(15,6) NOT NULL,
                        std_dev DECIMAL(15,6) NOT NULL,
                        min_value DECIMAL(15,6) NOT NULL,
                        max_value DECIMAL(15,6) NOT NULL,
                        percentile_95 DECIMAL(15,6) NOT NULL,
                        percentile_99 DECIMAL(15,6) NOT NULL,
                        sample_count INTEGER NOT NULL DEFAULT 0,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Anomaly alerts table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS anomaly_alerts (
                        alert_id VARCHAR(255) PRIMARY KEY,
                        alert_type VARCHAR(50) NOT NULL,
                        severity VARCHAR(20) NOT NULL,
                        metric_name VARCHAR(255) NOT NULL,
                        current_value DECIMAL(15,6) NOT NULL,
                        expected_min DECIMAL(15,6) NOT NULL,
                        expected_max DECIMAL(15,6) NOT NULL,
                        deviation_score DECIMAL(10,4) NOT NULL,
                        confidence DECIMAL(5,4) NOT NULL,
                        description TEXT,
                        affected_components JSONB,
                        suggested_actions JSONB,
                        detected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP WITH TIME ZONE,
                        resolved BOOLEAN DEFAULT false
                    );
                """)
                
                # Anomaly detection events log
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS anomaly_events (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        event_type VARCHAR(50) NOT NULL, -- 'detected', 'resolved', 'escalated'
                        alert_id VARCHAR(255) NOT NULL,
                        metric_name VARCHAR(255) NOT NULL,
                        value DECIMAL(15,6) NOT NULL,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        context_data JSONB
                    );
                """)
                
                # System health snapshots
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_health_snapshots (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        snapshot_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        overall_health_score DECIMAL(5,2) NOT NULL,
                        metrics_summary JSONB NOT NULL,
                        active_alerts_count INTEGER DEFAULT 0,
                        anomaly_score DECIMAL(10,6) DEFAULT 0
                    );
                """)
                
                # Create indexes
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_alerts_severity_time 
                    ON anomaly_alerts(severity, detected_at DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_events_alert_time 
                    ON anomaly_events(alert_id, timestamp DESC);
                """)
                
                self.logger.info("✅ Anomaly detection tables created")
                
        except Exception as e:
            self.logger.error(f"Failed to create anomaly tables: {e}")
            raise
    
    async def _load_existing_baselines(self):
        """Load existing metric baselines from database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                baselines = await conn.fetch("""
                    SELECT * FROM metric_baselines 
                    WHERE updated_at >= $1
                """, datetime.now() - timedelta(days=1))
                
                for row in baselines:
                    baseline = MetricBaseline(
                        metric_name=row['metric_name'],
                        mean=float(row['mean_value']),
                        std_dev=float(row['std_dev']),
                        min_value=float(row['min_value']),
                        max_value=float(row['max_value']),
                        percentile_95=float(row['percentile_95']),
                        percentile_99=float(row['percentile_99']),
                        sample_count=row['sample_count'],
                        last_updated=row['updated_at'].isoformat()
                    )
                    
                    self.baselines[baseline.metric_name] = baseline
                
                self.logger.info(f"📊 Loaded {len(self.baselines)} existing baselines")
                
        except Exception as e:
            self.logger.error(f"Failed to load existing baselines: {e}")
    
    async def _calculate_baselines(self):
        """Calculate baselines from historical performance data"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                # Get historical performance metrics
                cutoff_date = datetime.now() - timedelta(days=self.baseline_window_days)
                
                metrics_data = await conn.fetch("""
                    SELECT 
                        'response_time_ms' as metric_name,
                        response_time_ms as value
                    FROM model_performance_metrics 
                    WHERE created_at >= $1 AND response_time_ms IS NOT NULL
                    
                    UNION ALL
                    
                    SELECT 
                        'error_rate' as metric_name,
                        CASE WHEN success THEN 0.0 ELSE 1.0 END as value
                    FROM model_performance_metrics 
                    WHERE created_at >= $1
                    
                    UNION ALL
                    
                    SELECT 
                        'tokens_per_second' as metric_name,
                        tokens_per_second as value
                    FROM model_performance_metrics 
                    WHERE created_at >= $1 AND tokens_per_second IS NOT NULL
                """, cutoff_date)
                
                # Get system metrics from performance tracker
                system_metrics = await conn.fetch("""
                    SELECT 
                        metric_name,
                        value
                    FROM (
                        SELECT 'cpu_percent' as metric_name, 
                               CAST(value AS DECIMAL) as value
                        FROM performance_metrics 
                        WHERE metric_name = 'system_cpu_percent' 
                        AND timestamp >= $1
                        
                        UNION ALL
                        
                        SELECT 'memory_percent' as metric_name,
                               CAST(value AS DECIMAL) as value
                        FROM performance_metrics 
                        WHERE metric_name = 'system_memory_percent' 
                        AND timestamp >= $1
                    ) combined
                """, cutoff_date)
                
                # Combine all metrics
                all_metrics = list(metrics_data) + list(system_metrics)
                
                # Group by metric name
                metric_groups = defaultdict(list)
                for row in all_metrics:
                    if row['value'] is not None:
                        metric_groups[row['metric_name']].append(float(row['value']))
                
                # Calculate baselines for each metric
                new_baselines = 0
                for metric_name, values in metric_groups.items():
                    if len(values) >= 10:  # Minimum samples for reliable baseline
                        baseline = await self._calculate_metric_baseline(metric_name, values)
                        if baseline:
                            await self._store_baseline(baseline)
                            self.baselines[metric_name] = baseline
                            new_baselines += 1
                
                self.logger.info(f"📈 Calculated {new_baselines} new baselines from {len(all_metrics)} data points")
                
        except Exception as e:
            self.logger.error(f"Failed to calculate baselines: {e}")
    
    async def _calculate_metric_baseline(self, metric_name: str, values: List[float]) -> Optional[MetricBaseline]:
        """Calculate baseline statistics for a metric"""
        try:
            if len(values) < 10:
                return None
            
            values = np.array(values)
            
            # Remove extreme outliers (beyond 3 standard deviations)
            mean = np.mean(values)
            std = np.std(values)
            filtered_values = values[np.abs(values - mean) <= 3 * std]
            
            if len(filtered_values) < 5:
                filtered_values = values  # Keep original if too many outliers
            
            baseline = MetricBaseline(
                metric_name=metric_name,
                mean=float(np.mean(filtered_values)),
                std_dev=float(np.std(filtered_values)),
                min_value=float(np.min(filtered_values)),
                max_value=float(np.max(filtered_values)),
                percentile_95=float(np.percentile(filtered_values, 95)),
                percentile_99=float(np.percentile(filtered_values, 99)),
                sample_count=len(filtered_values),
                last_updated=datetime.now().isoformat()
            )
            
            return baseline
            
        except Exception as e:
            self.logger.error(f"Failed to calculate baseline for {metric_name}: {e}")
            return None
    
    async def _store_baseline(self, baseline: MetricBaseline):
        """Store baseline in database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO metric_baselines 
                    (metric_name, mean_value, std_dev, min_value, max_value, 
                     percentile_95, percentile_99, sample_count, updated_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, CURRENT_TIMESTAMP)
                    ON CONFLICT (metric_name) DO UPDATE
                    SET mean_value = $2, std_dev = $3, min_value = $4, max_value = $5,
                        percentile_95 = $6, percentile_99 = $7, sample_count = $8,
                        updated_at = CURRENT_TIMESTAMP
                """, baseline.metric_name, baseline.mean, baseline.std_dev,
                    baseline.min_value, baseline.max_value, baseline.percentile_95,
                    baseline.percentile_99, baseline.sample_count)
                    
        except Exception as e:
            self.logger.error(f"Failed to store baseline: {e}")
    
    async def _train_ml_models(self):
        """Train ML models for anomaly detection"""
        try:
            if not self.db_pool:
                return
            
            # Collect recent performance data for training
            async with self.db_pool.acquire() as conn:
                training_data = await conn.fetch("""
                    SELECT 
                        response_time_ms,
                        tokens_per_second,
                        CASE WHEN success THEN 0 ELSE 1 END as error_flag,
                        tokens_generated
                    FROM model_performance_metrics 
                    WHERE created_at >= $1 
                    AND response_time_ms IS NOT NULL 
                    AND tokens_per_second IS NOT NULL
                    AND tokens_generated > 0
                    LIMIT 1000
                """, datetime.now() - timedelta(days=7))
                
                if len(training_data) < 50:
                    self.logger.warning("Insufficient data for ML model training")
                    return
                
                # Prepare training data
                features = []
                for row in training_data:
                    features.append([
                        float(row['response_time_ms']),
                        float(row['tokens_per_second']),
                        float(row['error_flag']),
                        float(row['tokens_generated'])
                    ])
                
                features = np.array(features)
                
                # Scale features
                features_scaled = self.scaler.fit_transform(features)
                
                # Train isolation forest
                self.isolation_forest.fit(features_scaled)
                self.model_trained = True
                
                self.logger.info(f"🤖 Trained ML models with {len(features)} samples")
                
        except Exception as e:
            self.logger.error(f"Failed to train ML models: {e}")
            self.model_trained = False
    
    async def detect_anomaly(self, metric_name: str, value: float, context: Dict[str, Any] = None) -> Optional[AnomalyAlert]:
        """Detect if a metric value is anomalous"""
        try:
            baseline = self.baselines.get(metric_name)
            if not baseline:
                # No baseline available, cannot detect anomaly
                return None
            
            rule = self.monitoring_rules.get(metric_name, {})
            threshold_multiplier = rule.get('threshold_multiplier', 2.5)
            
            # Calculate deviation score
            if baseline.std_dev > 0:
                z_score = abs(value - baseline.mean) / baseline.std_dev
            else:
                z_score = 0
            
            # Check if value is anomalous
            upper_bound = baseline.mean + (threshold_multiplier * baseline.std_dev)
            lower_bound = baseline.mean - (threshold_multiplier * baseline.std_dev)
            
            is_anomaly = value > upper_bound or value < lower_bound
            
            if not is_anomaly:
                return None
            
            # Determine severity
            severity = self._calculate_severity(metric_name, value, z_score, rule)
            
            # Calculate confidence based on deviation and sample size
            confidence = min(0.99, z_score / 5.0)  # Higher z-score = higher confidence
            confidence *= min(1.0, baseline.sample_count / 100)  # More samples = higher confidence
            
            if confidence < self.confidence_threshold:
                return None
            
            # Generate alert
            alert_id = f"anomaly_{metric_name}_{int(datetime.now().timestamp())}"
            
            alert = AnomalyAlert(
                alert_id=alert_id,
                alert_type=self._classify_alert_type(metric_name),
                severity=severity,
                metric_name=metric_name,
                current_value=value,
                expected_range=(lower_bound, upper_bound),
                deviation_score=z_score,
                confidence=confidence,
                description=self._generate_alert_description(metric_name, value, baseline, z_score),
                affected_components=self._identify_affected_components(metric_name, context),
                suggested_actions=self._generate_suggested_actions(metric_name, value, severity),
                detected_at=datetime.now().isoformat()
            )
            
            # Store alert
            await self._store_alert(alert)
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            self.logger.warning(f"🚨 Anomaly detected: {metric_name}={value:.2f} (z-score: {z_score:.2f}, severity: {severity})")
            
            return alert
            
        except Exception as e:
            self.logger.error(f"Failed to detect anomaly for {metric_name}: {e}")
            return None
    
    def _calculate_severity(self, metric_name: str, value: float, z_score: float, rule: Dict) -> str:
        """Calculate severity level for an anomaly"""
        severity_levels = rule.get('severity_levels', {})
        
        # Check absolute value thresholds
        if 'critical' in severity_levels and value >= severity_levels['critical']:
            return 'critical'
        elif 'high' in severity_levels and value >= severity_levels['high']:
            return 'high'
        elif 'medium' in severity_levels and value >= severity_levels['medium']:
            return 'medium'
        
        # Check z-score based severity
        if z_score >= 5.0:
            return 'critical'
        elif z_score >= 3.5:
            return 'high'
        elif z_score >= 2.5:
            return 'medium'
        else:
            return 'low'
    
    def _classify_alert_type(self, metric_name: str) -> str:
        """Classify alert type based on metric name"""
        if 'response_time' in metric_name or 'duration' in metric_name:
            return 'performance'
        elif 'error' in metric_name or 'success' in metric_name:
            return 'error_rate'
        elif 'cost' in metric_name or 'budget' in metric_name:
            return 'cost'
        elif 'cpu' in metric_name or 'memory' in metric_name or 'disk' in metric_name:
            return 'resource'
        else:
            return 'usage'
    
    def _generate_alert_description(self, metric_name: str, value: float, baseline: MetricBaseline, z_score: float) -> str:
        """Generate human-readable alert description"""
        if value > baseline.mean:
            direction = "higher"
        else:
            direction = "lower"
        
        return (
            f"{metric_name} is significantly {direction} than expected. "
            f"Current value: {value:.2f}, Expected range: {baseline.mean - 2*baseline.std_dev:.2f} - {baseline.mean + 2*baseline.std_dev:.2f}. "
            f"Deviation: {z_score:.1f} standard deviations from normal."
        )
    
    def _identify_affected_components(self, metric_name: str, context: Dict[str, Any] = None) -> List[str]:
        """Identify system components affected by the anomaly"""
        components = []
        
        if 'response_time' in metric_name:
            components.extend(['llm_router', 'model_performance'])
        elif 'error' in metric_name:
            components.extend(['agent_execution', 'model_calls'])
        elif 'cpu' in metric_name or 'memory' in metric_name:
            components.extend(['system_resources', 'daemon_process'])
        elif 'cost' in metric_name:
            components.extend(['budget_manager', 'api_calls'])
        
        if context:
            if context.get('model_key'):
                components.append(f"model_{context['model_key']}")
            if context.get('project_id'):
                components.append(f"project_{context['project_id']}")
        
        return components
    
    def _generate_suggested_actions(self, metric_name: str, value: float, severity: str) -> List[str]:
        """Generate suggested actions for resolving the anomaly"""
        actions = []
        
        if 'response_time' in metric_name:
            if severity in ['high', 'critical']:
                actions.extend([
                    "Check system resources (CPU, memory)",
                    "Review recent model performance metrics",
                    "Consider switching to faster local models",
                    "Check for network connectivity issues"
                ])
            else:
                actions.extend([
                    "Monitor for trend continuation",
                    "Review recent task complexity changes"
                ])
        
        elif 'error' in metric_name:
            actions.extend([
                "Review recent error logs",
                "Check model availability and health",
                "Verify API keys and configurations",
                "Consider enabling fallback models"
            ])
        
        elif 'cpu' in metric_name or 'memory' in metric_name:
            if severity in ['high', 'critical']:
                actions.extend([
                    "Restart Kairos daemon to free resources",
                    "Check for memory leaks in running processes",
                    "Scale up system resources if possible",
                    "Review and optimize resource-intensive operations"
                ])
        
        elif 'cost' in metric_name:
            actions.extend([
                "Review recent API usage patterns",
                "Check if budget limits are appropriate",
                "Consider using more local models",
                "Analyze cost per task trends"
            ])
        
        # Always include general monitoring advice
        actions.append("Continue monitoring for pattern development")
        
        return actions
    
    async def _store_alert(self, alert: AnomalyAlert):
        """Store alert in database"""
        if not self.db_pool:
            return
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO anomaly_alerts 
                    (alert_id, alert_type, severity, metric_name, current_value,
                     expected_min, expected_max, deviation_score, confidence,
                     description, affected_components, suggested_actions)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """, alert.alert_id, alert.alert_type, alert.severity, alert.metric_name,
                    alert.current_value, alert.expected_range[0], alert.expected_range[1],
                    alert.deviation_score, alert.confidence, alert.description,
                    json.dumps(alert.affected_components), json.dumps(alert.suggested_actions))
                
                # Log detection event
                await conn.execute("""
                    INSERT INTO anomaly_events (event_type, alert_id, metric_name, value)
                    VALUES ('detected', $1, $2, $3)
                """, alert.alert_id, alert.metric_name, alert.current_value)
                
        except Exception as e:
            self.logger.error(f"Failed to store alert: {e}")
    
    async def resolve_alert(self, alert_id: str, resolution_note: str = None):
        """Mark an alert as resolved"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now().isoformat()
            
            if self.db_pool:
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.execute("""
                            UPDATE anomaly_alerts 
                            SET resolved = true, resolved_at = CURRENT_TIMESTAMP
                            WHERE alert_id = $1
                        """, alert_id)
                        
                        # Log resolution event
                        await conn.execute("""
                            INSERT INTO anomaly_events 
                            (event_type, alert_id, metric_name, value, context_data)
                            VALUES ('resolved', $1, $2, $3, $4)
                        """, alert_id, alert.metric_name, alert.current_value,
                            json.dumps({'resolution_note': resolution_note}))
                        
                except Exception as e:
                    self.logger.error(f"Failed to resolve alert in database: {e}")
            
            del self.active_alerts[alert_id]
            self.logger.info(f"✅ Resolved anomaly alert: {alert_id}")
    
    async def get_active_alerts(self, severity_filter: str = None) -> List[AnomalyAlert]:
        """Get all active alerts, optionally filtered by severity"""
        alerts = list(self.active_alerts.values())
        
        if severity_filter:
            alerts = [a for a in alerts if a.severity == severity_filter]
        
        # Sort by severity and detection time
        severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: (severity_order.get(x.severity, 4), x.detected_at), reverse=True)
        
        return alerts
    
    async def get_system_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        try:
            # Base health score
            health_score = 100.0
            
            # Deduct points for active alerts
            critical_alerts = len([a for a in self.active_alerts.values() if a.severity == 'critical'])
            high_alerts = len([a for a in self.active_alerts.values() if a.severity == 'high'])
            medium_alerts = len([a for a in self.active_alerts.values() if a.severity == 'medium'])
            low_alerts = len([a for a in self.active_alerts.values() if a.severity == 'low'])
            
            health_score -= critical_alerts * 25  # 25 points per critical alert
            health_score -= high_alerts * 15      # 15 points per high alert
            health_score -= medium_alerts * 8     # 8 points per medium alert
            health_score -= low_alerts * 3        # 3 points per low alert
            
            health_score = max(0, health_score)
            
            # Determine health status
            if health_score >= 90:
                status = "excellent"
            elif health_score >= 75:
                status = "good"
            elif health_score >= 50:
                status = "fair"
            elif health_score >= 25:
                status = "poor"
            else:
                status = "critical"
            
            # Store health snapshot
            if self.db_pool:
                try:
                    async with self.db_pool.acquire() as conn:
                        await conn.execute("""
                            INSERT INTO system_health_snapshots 
                            (overall_health_score, metrics_summary, active_alerts_count)
                            VALUES ($1, $2, $3)
                        """, health_score, json.dumps({
                            'critical_alerts': critical_alerts,
                            'high_alerts': high_alerts,
                            'medium_alerts': medium_alerts,
                            'low_alerts': low_alerts
                        }), len(self.active_alerts))
                except Exception as e:
                    self.logger.debug(f"Failed to store health snapshot: {e}")
            
            return {
                'health_score': round(health_score, 1),
                'status': status,
                'active_alerts': {
                    'critical': critical_alerts,
                    'high': high_alerts,
                    'medium': medium_alerts,
                    'low': low_alerts,
                    'total': len(self.active_alerts)
                },
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate health score: {e}")
            return {
                'health_score': 50.0,
                'status': 'unknown',
                'active_alerts': {'total': 0},
                'error': str(e)
            }
    
    async def _background_monitoring(self):
        """Background task for continuous monitoring"""
        while True:
            try:
                # Check for stale alerts (older than 24 hours)
                current_time = datetime.now()
                stale_alerts = []
                
                for alert_id, alert in self.active_alerts.items():
                    alert_time = datetime.fromisoformat(alert.detected_at.replace('Z', '+00:00'))
                    if (current_time - alert_time.replace(tzinfo=None)).total_seconds() > 86400:  # 24 hours
                        stale_alerts.append(alert_id)
                
                # Auto-resolve stale alerts
                for alert_id in stale_alerts:
                    await self.resolve_alert(alert_id, "Auto-resolved: No recent occurrences")
                
                # Refresh baselines if needed (once per hour)
                if current_time.minute == 0:  # Top of the hour
                    await self._calculate_baselines()
                
                # Sleep for 5 minutes before next check
                await asyncio.sleep(300)
                
            except Exception as e:
                self.logger.error(f"Background monitoring error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

# Global anomaly detector instance
anomaly_detector = None

async def get_anomaly_detector() -> AnomalyDetector:
    """Get global anomaly detector instance"""
    global anomaly_detector
    if anomaly_detector is None:
        anomaly_detector = AnomalyDetector()
        await anomaly_detector.initialize()
    return anomaly_detector
