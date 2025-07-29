"""
Budget Management Module for Kairos LLM Cost Control
Handles API cost tracking, budget limits, and automatic fallback mechanisms.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_HALF_UP
import json
import asyncpg
import redis.asyncio as redis
from src.core.config import get_config

@dataclass
class BudgetTransaction:
    """Represents a budget transaction"""
    id: Optional[str] = None
    project_id: str = "default"
    model_key: str = ""
    cost_usd: Decimal = Decimal('0')
    tokens_used: int = 0
    timestamp: str = ""
    task_type: str = "general"
    session_id: Optional[str] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

@dataclass
class BudgetStatus:
    """Current budget status"""
    project_id: str
    monthly_limit: Decimal
    current_usage: Decimal
    remaining: Decimal
    percentage_used: float
    is_over_budget: bool
    days_remaining_in_month: int
    estimated_monthly_cost: Decimal
    warning_threshold_reached: bool

class BudgetManager:
    """Manages API costs, budgets, and automatic fallback mechanisms"""
    
    def __init__(self, config: Dict[str, Any] = None, db_pool=None, redis_client=None):
        self.logger = logging.getLogger(__name__)
        if config:
            self.config = config
        else:
            try:
                kairos_config = get_config()
                self.config = {
                    'llm': {
                        'budget': {
                            'enabled': True,
                            'monthly_limit_usd': 50.0,
                            'warning_threshold_percent': 80,
                            'auto_fallback_on_limit': True,
                            'reset_day': 1
                        }
                    }
                }
            except Exception as e:
                self.logger.warning(f"Could not load config, using defaults: {e}")
                self.config = {
                    'llm': {
                        'budget': {
                            'enabled': True,
                            'monthly_limit_usd': 50.0,
                            'warning_threshold_percent': 80,
                            'auto_fallback_on_limit': True,
                            'reset_day': 1
                        }
                    }
                }
        self.db_pool = db_pool
        self.redis_client = redis_client
        
        # Budget configuration
        self.budget_config = self.config.get('llm', {}).get('budget', {})
        self.enabled = self.budget_config.get('enabled', True)
        self.monthly_limit = Decimal(str(self.budget_config.get('monthly_limit_usd', 50.0)))
        self.project_limits = self.budget_config.get('project_limits', {})
        self.warning_threshold = self.budget_config.get('warning_threshold_percent', 80) / 100
        self.auto_fallback = self.budget_config.get('auto_fallback_on_limit', True)
        self.reset_day = self.budget_config.get('reset_day', 1)
        
        # Model pricing (USD per 1K tokens)
        self.model_pricing = {
            # Ollama models are free
            'ollama': {'input': Decimal('0'), 'output': Decimal('0')},
            
            # Gemini pricing
            'gemini-1.5-flash': {'input': Decimal('0.000075'), 'output': Decimal('0.0003')},
            'gemini-1.5-pro': {'input': Decimal('0.00125'), 'output': Decimal('0.005')},
            
            # OpenRouter pricing (approximate)
            'anthropic/claude-3-sonnet': {'input': Decimal('0.003'), 'output': Decimal('0.015')},
            'meta-llama/llama-3-70b': {'input': Decimal('0.0008'), 'output': Decimal('0.0008')},
            
            # Default fallback pricing
            'default': {'input': Decimal('0.001'), 'output': Decimal('0.002')}
        }
        
        # Cache for budget status
        self.status_cache = {}
        self.cache_ttl = 300  # 5 minutes
        
        self.logger.info(f"💰 Budget Manager initialized - Monthly limit: ${self.monthly_limit}")
    
    async def initialize(self):
        """Initialize budget manager with database connections"""
        if not self.db_pool or not self.redis_client:
            self.logger.warning("Budget manager initialized without database connections")
        
        # Create budget tables if they don't exist
        if self.db_pool:
            await self._create_budget_tables()
    
    async def _create_budget_tables(self):
        """Create budget tracking tables"""
        try:
            async with self.db_pool.acquire() as conn:
                # Budget transactions table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS budget_transactions (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        project_id VARCHAR(255) NOT NULL DEFAULT 'default',
                        model_key VARCHAR(255) NOT NULL,
                        cost_usd DECIMAL(10,6) NOT NULL,
                        tokens_used INTEGER NOT NULL DEFAULT 0,
                        input_tokens INTEGER NOT NULL DEFAULT 0,
                        output_tokens INTEGER NOT NULL DEFAULT 0,
                        timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        task_type VARCHAR(100) DEFAULT 'general',
                        session_id VARCHAR(255),
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Budget limits table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS budget_limits (
                        project_id VARCHAR(255) PRIMARY KEY,
                        monthly_limit_usd DECIMAL(10,2) NOT NULL,
                        warning_threshold DECIMAL(3,2) DEFAULT 0.8,
                        auto_fallback_enabled BOOLEAN DEFAULT true,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # Budget alerts table
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS budget_alerts (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        project_id VARCHAR(255) NOT NULL,
                        alert_type VARCHAR(50) NOT NULL, -- 'warning', 'limit_reached', 'over_budget'
                        threshold_percent DECIMAL(5,2) NOT NULL,
                        current_usage_usd DECIMAL(10,6) NOT NULL,
                        limit_usd DECIMAL(10,2) NOT NULL,
                        triggered_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP WITH TIME ZONE,
                        resolved BOOLEAN DEFAULT false
                    );
                """)
                
                # Create indexes for performance
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_budget_transactions_project_timestamp 
                    ON budget_transactions(project_id, timestamp DESC);
                """)
                
                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_budget_transactions_model_timestamp 
                    ON budget_transactions(model_key, timestamp DESC);
                """)
                
                self.logger.info("✅ Budget tables created successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to create budget tables: {e}")
            raise
    
    def calculate_cost(
        self, 
        model_key: str, 
        input_tokens: int, 
        output_tokens: int
    ) -> Decimal:
        """Calculate cost for a model usage"""
        if not self.enabled:
            return Decimal('0')
        
        # Extract model name from key (format: provider_model)
        model_name = model_key.split('_', 1)[-1] if '_' in model_key else model_key
        
        # Get pricing for model
        pricing = self.model_pricing.get(model_name, self.model_pricing.get('default'))
        
        # Calculate cost (pricing is per 1K tokens)
        input_cost = (Decimal(input_tokens) / 1000) * pricing['input']
        output_cost = (Decimal(output_tokens) / 1000) * pricing['output']
        
        total_cost = input_cost + output_cost
        
        # Round to 6 decimal places
        return total_cost.quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP)
    
    async def record_usage(
        self,
        project_id: str,
        model_key: str,
        input_tokens: int,
        output_tokens: int,
        task_type: str = "general",
        session_id: Optional[str] = None
    ) -> BudgetTransaction:
        """Record API usage and cost"""
        if not self.enabled:
            return BudgetTransaction()
        
        cost = self.calculate_cost(model_key, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens
        
        transaction = BudgetTransaction(
            project_id=project_id,
            model_key=model_key,
            cost_usd=cost,
            tokens_used=total_tokens,
            task_type=task_type,
            session_id=session_id
        )
        
        # Store in database
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.fetchrow("""
                        INSERT INTO budget_transactions 
                        (project_id, model_key, cost_usd, tokens_used, input_tokens, 
                         output_tokens, task_type, session_id)
                        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        RETURNING id
                    """, project_id, model_key, float(cost), total_tokens, 
                        input_tokens, output_tokens, task_type, session_id)
                    
                    transaction.id = str(result['id'])
                    
                    # Clear cache for this project
                    cache_key = f"budget_status:{project_id}"
                    if self.redis_client:
                        await self.redis_client.delete(cache_key)
                    
                    # Check if we need to trigger alerts
                    await self._check_budget_alerts(project_id, cost)
                    
                    self.logger.debug(f"💰 Recorded usage: {project_id} - ${cost} for {total_tokens} tokens")
                    
            except Exception as e:
                self.logger.error(f"Failed to record budget usage: {e}")
        
        return transaction
    
    async def get_budget_status(self, project_id: str) -> BudgetStatus:
        """Get current budget status for a project"""
        if not self.enabled:
            return BudgetStatus(
                project_id=project_id,
                monthly_limit=Decimal('0'),
                current_usage=Decimal('0'),
                remaining=Decimal('0'),
                percentage_used=0.0,
                is_over_budget=False,
                days_remaining_in_month=30,
                estimated_monthly_cost=Decimal('0'),
                warning_threshold_reached=False
            )
        
        # Check cache first
        cache_key = f"budget_status:{project_id}"
        if self.redis_client:
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    # Convert Decimal fields back
                    for field in ['monthly_limit', 'current_usage', 'remaining', 'estimated_monthly_cost']:
                        data[field] = Decimal(str(data[field]))
                    return BudgetStatus(**data)
            except Exception as e:
                self.logger.debug(f"Cache lookup failed: {e}")
        
        # Get project limit
        project_limit = Decimal(str(self.project_limits.get(project_id, self.monthly_limit)))
        
        # Calculate current month usage
        now = datetime.now()
        month_start = datetime(now.year, now.month, self.reset_day)
        if now.day < self.reset_day:
            # Previous month
            if now.month == 1:
                month_start = datetime(now.year - 1, 12, self.reset_day)
            else:
                month_start = datetime(now.year, now.month - 1, self.reset_day)
        
        current_usage = Decimal('0')
        if self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    result = await conn.fetchval("""
                        SELECT COALESCE(SUM(cost_usd), 0)
                        FROM budget_transactions
                        WHERE project_id = $1 AND timestamp >= $2
                    """, project_id, month_start)
                    
                    current_usage = Decimal(str(result))
            except Exception as e:
                self.logger.error(f"Failed to get budget usage: {e}")
        
        # Calculate remaining budget
        remaining = project_limit - current_usage
        percentage_used = float(current_usage / project_limit * 100) if project_limit > 0 else 0
        is_over_budget = current_usage > project_limit
        
        # Calculate days remaining in current budget period
        next_reset = month_start + timedelta(days=32)  # Approximate next month
        next_reset = datetime(next_reset.year, next_reset.month, self.reset_day)
        days_remaining = (next_reset - now).days
        
        # Estimate monthly cost based on current usage
        days_elapsed = (now - month_start).days + 1
        estimated_monthly_cost = (current_usage / days_elapsed) * 30 if days_elapsed > 0 else current_usage
        
        # Check warning threshold
        warning_threshold_reached = percentage_used >= (self.warning_threshold * 100)
        
        status = BudgetStatus(
            project_id=project_id,
            monthly_limit=project_limit,
            current_usage=current_usage,
            remaining=remaining,
            percentage_used=percentage_used,
            is_over_budget=is_over_budget,
            days_remaining_in_month=days_remaining,
            estimated_monthly_cost=estimated_monthly_cost,
            warning_threshold_reached=warning_threshold_reached
        )
        
        # Cache the status
        if self.redis_client:
            try:
                # Convert Decimal fields to strings for JSON serialization
                cache_data = asdict(status)
                for field in ['monthly_limit', 'current_usage', 'remaining', 'estimated_monthly_cost']:
                    cache_data[field] = str(cache_data[field])
                
                await self.redis_client.setex(
                    cache_key, 
                    self.cache_ttl, 
                    json.dumps(cache_data)
                )
            except Exception as e:
                self.logger.debug(f"Failed to cache budget status: {e}")
        
        return status
    
    async def should_use_paid_model(self, project_id: str, estimated_cost: Decimal = None) -> bool:
        """Check if we should use a paid model or fallback to free ones"""
        if not self.enabled or not self.auto_fallback:
            return True
        
        status = await self.get_budget_status(project_id)
        
        # If over budget, always use free models
        if status.is_over_budget:
            return False
        
        # If we have an estimated cost, check if it would put us over budget
        if estimated_cost and (status.current_usage + estimated_cost) > status.monthly_limit:
            return False
        
        return True
    
    async def _check_budget_alerts(self, project_id: str, new_cost: Decimal):
        """Check if budget alerts need to be triggered"""
        status = await self.get_budget_status(project_id)
        
        # Determine alert type
        alert_type = None
        if status.is_over_budget:
            alert_type = "over_budget"
        elif status.percentage_used >= 100:  # At limit
            alert_type = "limit_reached"
        elif status.warning_threshold_reached:
            alert_type = "warning"
        
        if alert_type and self.db_pool:
            try:
                async with self.db_pool.acquire() as conn:
                    # Check if we already have an unresolved alert of this type
                    existing = await conn.fetchval("""
                        SELECT id FROM budget_alerts
                        WHERE project_id = $1 AND alert_type = $2 AND resolved = false
                    """, project_id, alert_type)
                    
                    if not existing:
                        # Create new alert
                        await conn.execute("""
                            INSERT INTO budget_alerts 
                            (project_id, alert_type, threshold_percent, 
                             current_usage_usd, limit_usd)
                            VALUES ($1, $2, $3, $4, $5)
                        """, project_id, alert_type, status.percentage_used,
                            float(status.current_usage), float(status.monthly_limit))
                        
                        self.logger.warning(
                            f"🚨 Budget alert triggered: {alert_type} for {project_id} "
                            f"- Usage: ${status.current_usage} / ${status.monthly_limit} "
                            f"({status.percentage_used:.1f}%)"
                        )
                        
            except Exception as e:
                self.logger.error(f"Failed to create budget alert: {e}")
    
    async def get_usage_analytics(
        self, 
        project_id: str = None, 
        days: int = 30
    ) -> Dict[str, Any]:
        """Get detailed usage analytics"""
        if not self.enabled or not self.db_pool:
            return {"error": "Budget tracking not enabled or no database connection"}
        
        try:
            async with self.db_pool.acquire() as conn:
                # Base query conditions
                where_conditions = ["timestamp >= $1"]
                params = [datetime.now() - timedelta(days=days)]
                
                if project_id:
                    where_conditions.append("project_id = $2")
                    params.append(project_id)
                
                where_clause = " AND ".join(where_conditions)
                
                # Total usage
                total_cost = await conn.fetchval(f"""
                    SELECT COALESCE(SUM(cost_usd), 0)
                    FROM budget_transactions
                    WHERE {where_clause}
                """, *params)
                
                # Usage by model
                model_usage = await conn.fetch(f"""
                    SELECT model_key, 
                           COUNT(*) as requests,
                           SUM(cost_usd) as total_cost,
                           SUM(tokens_used) as total_tokens,
                           AVG(cost_usd) as avg_cost_per_request
                    FROM budget_transactions
                    WHERE {where_clause}
                    GROUP BY model_key
                    ORDER BY total_cost DESC
                """, *params)
                
                # Usage by task type
                task_usage = await conn.fetch(f"""
                    SELECT task_type,
                           COUNT(*) as requests,
                           SUM(cost_usd) as total_cost,
                           AVG(cost_usd) as avg_cost_per_request
                    FROM budget_transactions
                    WHERE {where_clause}
                    GROUP BY task_type
                    ORDER BY total_cost DESC
                """, *params)
                
                # Daily usage trend
                daily_usage = await conn.fetch(f"""
                    SELECT DATE(timestamp) as date,
                           SUM(cost_usd) as daily_cost,
                           COUNT(*) as daily_requests
                    FROM budget_transactions
                    WHERE {where_clause}
                    GROUP BY DATE(timestamp)
                    ORDER BY date DESC
                    LIMIT 30
                """, *params)
                
                return {
                    "period_days": days,
                    "project_id": project_id,
                    "total_cost_usd": float(total_cost),
                    "model_breakdown": [
                        {
                            "model": row['model_key'],
                            "requests": row['requests'],
                            "total_cost": float(row['total_cost']),
                            "total_tokens": row['total_tokens'],
                            "avg_cost_per_request": float(row['avg_cost_per_request'])
                        }
                        for row in model_usage
                    ],
                    "task_breakdown": [
                        {
                            "task_type": row['task_type'],
                            "requests": row['requests'],
                            "total_cost": float(row['total_cost']),
                            "avg_cost_per_request": float(row['avg_cost_per_request'])
                        }
                        for row in task_usage
                    ],
                    "daily_trend": [
                        {
                            "date": row['date'].isoformat(),
                            "cost": float(row['daily_cost']),
                            "requests": row['daily_requests']
                        }
                        for row in daily_usage
                    ],
                    "generated_at": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get usage analytics: {e}")
            return {"error": str(e)}
    
    async def set_project_budget(self, project_id: str, monthly_limit_usd: float):
        """Set budget limit for a specific project"""
        if not self.enabled or not self.db_pool:
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO budget_limits (project_id, monthly_limit_usd)
                    VALUES ($1, $2)
                    ON CONFLICT (project_id) DO UPDATE
                    SET monthly_limit_usd = $2, updated_at = CURRENT_TIMESTAMP
                """, project_id, monthly_limit_usd)
                
                # Update in-memory cache
                self.project_limits[project_id] = monthly_limit_usd
                
                # Clear status cache
                if self.redis_client:
                    await self.redis_client.delete(f"budget_status:{project_id}")
                
                self.logger.info(f"💰 Updated budget for {project_id}: ${monthly_limit_usd}/month")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to set project budget: {e}")
            return False
    
    async def get_cost_estimates(self) -> Dict[str, Any]:
        """Get cost estimates for different models"""
        return {
            "pricing_per_1k_tokens": {
                model: {
                    "input": str(pricing['input']),
                    "output": str(pricing['output']),
                    "avg_cost_per_1k": str((pricing['input'] + pricing['output']) / 2)
                }
                for model, pricing in self.model_pricing.items()
                if model != 'default'
            },
            "sample_costs": {
                "short_response_500_tokens": {
                    model: str(self.calculate_cost(model, 100, 400))
                    for model in self.model_pricing.keys()
                    if model != 'default'
                },
                "long_response_2000_tokens": {
                    model: str(self.calculate_cost(model, 500, 1500))
                    for model in self.model_pricing.keys()
                    if model != 'default'
                }
            },
            "free_models": [
                model for model, pricing in self.model_pricing.items()
                if pricing['input'] == Decimal('0') and pricing['output'] == Decimal('0')
            ]
        }

# Global budget manager instance
budget_manager = None

async def get_budget_manager() -> BudgetManager:
    """Get global budget manager instance"""
    global budget_manager
    if budget_manager is None:
        budget_manager = BudgetManager()
        await budget_manager.initialize()
    return budget_manager
