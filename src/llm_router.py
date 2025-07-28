import httpx
import json
import logging
import time
import hashlib
import asyncpg
import redis.asyncio as redis
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from decimal import Decimal
from mcp import mcp, MCPContext, MCPMessage, MCPMessageType, MCPRole
from .analytics.budget_manager import BudgetManager, get_budget_manager

class LLMRouter:
    """Routes LLM requests to best available model based on task type and performance"""
    
    def __init__(self, db_config: Dict[str, str] = None, redis_url: str = None):
        self.logger = logging.getLogger(__name__)
        self.ollama_base_url = "http://localhost:11434"
        self.performance_metrics = {}
        self.model_health_status = {}
        self.fallback_chain = []
        self.context_cache = {}
        
        # Database connections
        self.db_config = db_config or {
            'host': 'localhost',
            'port': 5432,
            'database': 'kairos_db',
            'user': 'kairos_user',
            'password': 'secure_password'
        }
        self.redis_url = redis_url or "redis://localhost:6379"
        self.db_pool = None
        self.redis_client = None
        
        # Enhanced model configuration with detailed capabilities
        self.models = {
            "ollama": {
                "available_models": [
                    "deepseek-r1:8b",
                    "llama3.1:8b", 
                    "qwen2.5-coder:latest",
                    "mistral:latest",
                    "codellama:latest",
                    "phi3:medium",
                    "gemma2:latest"
                ],
                "cost": 0.0,  # Free local
                "speed_rank": 8,
                "quality_rank": 7,
                "specialties": ["coding", "reasoning", "general"],
                "max_context": 8192,
                "optimal_tasks": ["code_generation", "local_reasoning", "fast_responses"]
            },
            "gemini": {
                "models": ["gemini-1.5-flash", "gemini-1.5-pro"],
                "cost": 0.001,  # Very low cost
                "speed_rank": 9,
                "quality_rank": 8,
                "specialties": ["analysis", "reasoning", "multimodal"],
                "max_context": 32768,
                "optimal_tasks": ["complex_analysis", "research", "multimodal_processing"]
            },
            "openrouter": {
                "models": ["anthropic/claude-3-sonnet", "meta-llama/llama-3-70b"],
                "cost": 0.01,
                "speed_rank": 7,
                "quality_rank": 9,
                "specialties": ["complex_reasoning", "creative"],
                "max_context": 200000,
                "optimal_tasks": ["complex_reasoning", "creative_writing", "long_context"]
            }
        }
        
        # Model selection weights for scoring
        self.selection_weights = {
            "performance": 0.4,
            "specialization": 0.3,
            "availability": 0.2,
            "cost": 0.1
        }
        
        # Initialize fallback chain
        self._initialize_fallback_chain()
        
        # Start health monitoring
        self._start_health_monitoring()
        
        # LoRA adapters management
        self.adapter_base_path = Path("models/lora_adapters")
        self.adapter_base_path.mkdir(parents=True, exist_ok=True)
        self.loaded_adapters = {}
        
        # Load available LoRA adapters at startup
        self._discover_lora_adapters()
        
    def _discover_lora_adapters(self):
        """Discover and load available LoRA adapters"""
        if not self.adapter_base_path.exists():
            self.adapter_base_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("Created LoRA adapters directory")
            return
            
        # Load all available adapters
        adapter_count = 0
        for adapter_dir in self.adapter_base_path.iterdir():
            if adapter_dir.is_dir():
                if self.load_adapter(adapter_dir.name):
                    adapter_count += 1
                    
        self.logger.info(f"📦 Discovered {adapter_count} LoRA adapters")
        
    async def initialize_connections(self):
        """Initialize database and cache connections"""
        try:
            # Initialize PostgreSQL connection pool
            self.db_pool = await asyncpg.create_pool(**self.db_config)
            self.logger.info("✅ PostgreSQL connection pool created")
            
            # Initialize Redis client
            self.redis_client = await redis.from_url(self.redis_url)
            await self.redis_client.ping()
            self.logger.info("✅ Redis connection established")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize connections: {e}")
            raise
    
    async def close_connections(self):
        """Close database and cache connections"""
        if self.db_pool:
            await self.db_pool.close()
        if self.redis_client:
            await self.redis_client.close()
    
    async def _calculate_model_score(self, model_key: str, task_type: str, project_id: str = None) -> float:
        """Calculate performance score for a model based on historical metrics"""
        if not self.db_pool:
            return 0.5  # Default score if no database
            
        try:
            async with self.db_pool.acquire() as conn:
                # Call the PostgreSQL function to calculate score
                score = await conn.fetchval(
                    "SELECT calculate_model_score($1, $2)",
                    model_key, task_type
                )
                return float(score) if score else 0.5
        except Exception as e:
            self.logger.error(f"Failed to calculate model score: {e}")
            return 0.5
    
    async def _get_cached_response(self, prompt: str, model_key: str) -> Optional[str]:
        """Check Redis cache for existing response"""
        if not self.redis_client:
            return None
            
        # Generate cache key
        cache_key = hashlib.sha256(f"{prompt}:{model_key}".encode()).hexdigest()
        
        try:
            # Check Redis first
            cached = await self.redis_client.get(f"llm_cache:{cache_key}")
            if cached:
                self.logger.info(f"Cache hit for prompt hash: {cache_key[:8]}...")
                return json.loads(cached)
                
            # Check PostgreSQL cache table
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    result = await conn.fetchrow(
                        """
                        UPDATE llm_response_cache 
                        SET hit_count = hit_count + 1, last_accessed = CURRENT_TIMESTAMP
                        WHERE cache_key = $1 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
                        RETURNING response
                        """,
                        cache_key
                    )
                    if result:
                        # Store in Redis for faster access
                        await self.redis_client.setex(
                            f"llm_cache:{cache_key}",
                            3600,  # 1 hour TTL
                            json.dumps(result['response'])
                        )
                        return result['response']
                        
        except Exception as e:
            self.logger.error(f"Cache lookup failed: {e}")
            
        return None
    
    async def _store_cached_response(self, prompt: str, model_key: str, response: str, ttl_hours: int = 24):
        """Store response in cache"""
        cache_key = hashlib.sha256(f"{prompt}:{model_key}".encode()).hexdigest()
        
        try:
            # Store in Redis
            if self.redis_client:
                await self.redis_client.setex(
                    f"llm_cache:{cache_key}",
                    ttl_hours * 3600,
                    json.dumps(response)
                )
                
            # Store in PostgreSQL
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO llm_response_cache (cache_key, model_key, prompt, response, expires_at)
                        VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP + INTERVAL '%s hours')
                        ON CONFLICT (cache_key) DO UPDATE
                        SET response = $4, hit_count = 0, last_accessed = CURRENT_TIMESTAMP
                        """ % ttl_hours,
                        cache_key, model_key, prompt, response
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to cache response: {e}")
    
    async def _record_performance_metric(self, model_config: Dict, metrics: Dict):
        """Record performance metrics to database"""
        if not self.db_pool:
            return
            
        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO model_performance_metrics (
                        model_key, task_type, project_id,
                        response_time_ms, tokens_generated, tokens_per_second,
                        success, guardian_approved, error_message,
                        prompt_length, context_length, temperature,
                        task_id, session_id
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                    """,
                    f"{model_config['provider']}_{model_config['model']}",
                    model_config.get('task_type', 'general'),
                    metrics.get('project_id'),
                    metrics['response_time_ms'],
                    metrics.get('tokens_generated', 0),
                    metrics.get('tokens_per_second', 0),
                    metrics.get('success', True),
                    metrics.get('guardian_approved'),
                    metrics.get('error_message'),
                    metrics.get('prompt_length', 0),
                    metrics.get('context_length', 0),
                    metrics.get('temperature', 0.7),
                    metrics.get('task_id'),
                    metrics.get('session_id')
                )
        except Exception as e:
            self.logger.error(f"Failed to record performance metric: {e}")
        
    async def get_available_ollama_models(self) -> List[str]:
        """Get list of available Ollama models async"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{self.ollama_base_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models_data = response.json()
                    return [model["name"] for model in models_data.get("models", [])]
        except Exception as e:
            self.logger.error(f"Failed to get Ollama models: {e}")
        return []
        
    async def select_model(self, task: str, context: Dict = None) -> Dict[str, Any]:
        """Select best model for task based on requirements and performance"""
        
        task_type = self._classify_task(task)
        project_id = context.get('project_id', 'default') if context else 'default'
        
        # Get budget manager and check if we can use paid models
        budget_manager = await get_budget_manager()
        can_use_paid = await budget_manager.should_use_paid_model(project_id)
        
        # Get available models (with caching)
        available_models = await self.get_available_ollama_models()
        if not available_models:
            available_models = self.models["ollama"]["available_models"]
        
        # Calculate scores for each available model
        model_scores = {}
        for provider, config in self.models.items():
            if provider == "ollama":
                for model in config["available_models"]:
                    if model in available_models:
                        model_key = f"{provider}_{model}"
                        # Get historical performance score
                        perf_score = await self._calculate_model_score(model_key, task_type, project_id)
                        
                        # Calculate specialization score
                        spec_score = 1.0 if task_type in config["specialties"] else 0.5
                        
                        # Calculate availability score (always 1.0 for available models)
                        avail_score = 1.0
                        
                        # Calculate cost score (local models are free, so perfect score)
                        cost_score = 1.0 - config["cost"]
                        
                        # Calculate weighted total score
                        total_score = (
                            self.selection_weights["performance"] * perf_score +
                            self.selection_weights["specialization"] * spec_score +
                            self.selection_weights["availability"] * avail_score +
                            self.selection_weights["cost"] * cost_score
                        )
                        
                        model_scores[model] = {
                            "provider": provider,
                            "total_score": total_score,
                            "perf_score": perf_score,
                            "spec_score": spec_score
                        }
        
        # Select model with highest score
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1]["total_score"])
            selected_model = best_model[0]
            selected_provider = best_model[1]["provider"]
            self.logger.info(f"Selected {selected_model} with score {best_model[1]['total_score']:.3f} for {task_type} task")
        else:
            # Fallback to default
            selected_model = "llama3.1:8b"
            selected_provider = "ollama"
            self.logger.warning("No scored models available, using default")
            
        return {
            "provider": selected_provider,
            "model": selected_model,
            "task_type": task_type,
            "estimated_cost": self.models[selected_provider]["cost"],
            "selected_at": datetime.now().isoformat(),
            "scores": model_scores.get(selected_model, {})
        }
        
    def _classify_task(self, task: str) -> str:
        """Classify task type for routing"""
        task_lower = task.lower()
        
        if any(keyword in task_lower for keyword in ["code", "program", "function", "debug", "implement"]):
            return "coding"
        elif any(keyword in task_lower for keyword in ["reason", "think", "analyze", "logic", "solve"]):
            return "reasoning"
        elif any(keyword in task_lower for keyword in ["write", "create", "generate", "compose"]):
            return "creative"
        else:
            return "general"
            
    async def generate(self, prompt: str, model_config: Dict = None, context: Dict = None, mcp_context: MCPContext = None) -> Dict[str, Any]:
        """Generate response using selected model with caching and metrics"""
        start_time = time.time()
        
        if not model_config:
            model_config = await self.select_model(prompt, context)
            
        model_key = f"{model_config['provider']}_{model_config['model']}"
        
        # Check cache first
        cached_response = await self._get_cached_response(prompt, model_key)
        if cached_response:
            return {
                "response": cached_response,
                "model_config": model_config,
                "duration": 0.001,  # Near instant for cached response
                "cached": True,
                "timestamp": datetime.now().isoformat(),
                "mcp_context_id": mcp_context.context_id if mcp_context else None
            }
            
        try:
            # Prepare prompt with MCP context if available
            if mcp_context:
                enhanced_prompt = self._enhance_prompt_with_mcp(prompt, mcp_context)
            else:
                enhanced_prompt = prompt
                
            if model_config["provider"] == "ollama":
                response = await self._generate_ollama(enhanced_prompt, model_config["model"], mcp_context)
                response_text = response.get("response", "")
                
                # Parse MCP messages from response if context available
                if mcp_context:
                    mcp_messages = mcp.parse_llm_response(response_text, mcp_context.context_id)
                    for msg in mcp_messages:
                        await mcp.process_message(msg)
            else:
                response = {"error": "Provider not implemented yet"}
                response_text = ""
                
            # Track performance
            duration = time.time() - start_time
            response_time_ms = duration * 1000
            
            # Track budget usage
            project_id = context.get('project_id', 'default') if context else 'default'
            budget_manager = await get_budget_manager()
            
            # Estimate token counts (rough approximation)
            input_tokens = len(prompt.split()) * 1.3  # Rough conversion to tokens
            output_tokens = len(response_text.split()) * 1.3
            
            # Record budget usage
            if budget_manager.enabled:
                await budget_manager.record_usage(
                    project_id=project_id,
                    model_key=model_key,
                    input_tokens=int(input_tokens),
                    output_tokens=int(output_tokens),
                    task_type=model_config.get('task_type', 'general'),
                    session_id=context.get('session_id') if context else None
                )
            
            # Record metrics to database
            metrics = {
                "response_time_ms": response_time_ms,
                "tokens_generated": int(output_tokens),
                "tokens_per_second": int(output_tokens) / duration if duration > 0 else 0,
                "success": "error" not in response,
                "prompt_length": int(input_tokens),
                "project_id": project_id,
                "task_id": context.get('task_id') if context else None,
                "session_id": context.get('session_id') if context else None,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens)
            }
            await self._record_performance_metric(model_config, metrics)
            
            # Update in-memory metrics
            self._update_performance_metrics(model_config, duration, len(response_text))
            
            # Cache successful responses
            if "error" not in response and response_text:
                await self._store_cached_response(prompt, model_key, response_text)
            
            return {
                "response": response_text,
                "model_config": model_config,
                "duration": duration,
                "cached": False,
                "timestamp": datetime.now().isoformat(),
                "mcp_context_id": mcp_context.context_id if mcp_context else None,
                "metrics": metrics
            }
            
        except Exception as e:
            self.logger.error(f"Generation failed: {e}", exc_info=True)
            
            # Record failure metric
            await self._record_performance_metric(model_config, {
                "response_time_ms": (time.time() - start_time) * 1000,
                "success": False,
                "error_message": str(e),
                "project_id": context.get('project_id') if context else None
            })
            
            return {
                "error": str(e),
                "model_config": model_config,
                "duration": time.time() - start_time,
                "cached": False
            }
            
    async def _generate_ollama(self, prompt: str, model: str, mcp_context: MCPContext = None) -> Dict[str, Any]:
        """Generate response using Ollama with async httpx"""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        # Add MCP-specific parameters if context available
        if mcp_context:
            payload["options"] = {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 2048
            }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.ollama_base_url}/api/generate",
                json=payload,
                timeout=30
            )
        
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Ollama API error: {response.status_code}")
            
    def _update_performance_metrics(self, model_config: Dict, duration: float, response_length: int):
        """Update performance metrics for model selection optimization"""
        model_key = f"{model_config['provider']}_{model_config['model']}"
        
        if model_key not in self.performance_metrics:
            self.performance_metrics[model_key] = {
                "total_requests": 0,
                "avg_duration": 0,
                "avg_response_length": 0,
                "success_rate": 0
            }
            
        metrics = self.performance_metrics[model_key]
        metrics["total_requests"] += 1
        
        # Update running averages
        total_requests = metrics["total_requests"]
        metrics["avg_duration"] = ((metrics["avg_duration"] * (total_requests - 1)) + duration) / total_requests
        metrics["avg_response_length"] = ((metrics["avg_response_length"] * (total_requests - 1)) + response_length) / total_requests
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all models"""
        return {
            "metrics": self.performance_metrics,
            "available_ollama_models": [],  # Will be async call
            "total_requests": sum(m["total_requests"] for m in self.performance_metrics.values())
        }
        
    def _initialize_fallback_chain(self):
        """Initialize model fallback chain for reliability"""
        self.fallback_chain = [
            {"provider": "ollama", "models": ["llama3.1:8b", "mistral:latest"]},
            {"provider": "gemini", "models": ["gemini-1.5-flash"]},
            {"provider": "openrouter", "models": ["anthropic/claude-3-sonnet"]}
        ]
        self.logger.info("🔄 Fallback chain initialized")
        
    def _start_health_monitoring(self):
        """Start background health monitoring for models"""
        # For now, just log that monitoring is started
        # In a full implementation, this would start a background task
        self.logger.info("📊 Model health monitoring started")
        
    def get_model_health(self, model_key: str) -> Dict[str, Any]:
        """Get health status for a specific model"""
        return self.model_health_status.get(model_key, {
            "status": "unknown",
            "last_check": None,
            "response_time": None
        })
    
    def load_adapter(self, adapter_name: str) -> bool:
        """Load a LoRA adapter for fine-tuned models"""
        adapter_path = self.adapter_base_path / adapter_name
        
        if not adapter_path.exists():
            self.logger.error(f"Adapter {adapter_name} not found at {adapter_path}")
            return False
            
        try:
            # Load adapter metadata
            metadata_path = adapter_path / "metadata.json"
            if metadata_path.exists():
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
                    
                self.loaded_adapters[adapter_name] = {
                    "path": str(adapter_path),
                    "metadata": metadata,
                    "loaded_at": datetime.now().isoformat()
                }
                
                # Register the adapter-enhanced model
                base_model = metadata.get("base_model", "mistral:latest")
                enhanced_model_name = f"{base_model}+{adapter_name}"
                
                # Add to available models
                if enhanced_model_name not in self.models["ollama"]["available_models"]:
                    self.models["ollama"]["available_models"].append(enhanced_model_name)
                    
                self.logger.info(f"✅ Loaded LoRA adapter: {adapter_name} for {base_model}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to load adapter {adapter_name}: {e}")
            return False
            
    def list_loaded_adapters(self) -> List[Dict[str, Any]]:
        """List all currently loaded LoRA adapters"""
        return [
            {
                "name": name,
                "path": info["path"],
                "base_model": info["metadata"].get("base_model"),
                "training_samples": info["metadata"].get("training_samples"),
                "loaded_at": info["loaded_at"]
            }
            for name, info in self.loaded_adapters.items()
        ]
        
    async def initialize_adapters(self):
        """Initialize and load all available LoRA adapters"""
        if not self.adapter_base_path.exists():
            self.adapter_base_path.mkdir(parents=True, exist_ok=True)
            self.logger.info("Created LoRA adapters directory")
            return
            
        # Load all available adapters
        adapter_count = 0
        for adapter_dir in self.adapter_base_path.iterdir():
            if adapter_dir.is_dir():
                if self.load_adapter(adapter_dir.name):
                    adapter_count += 1
                    
        self.logger.info(f"📦 Loaded {adapter_count} LoRA adapters")
    
    def _enhance_prompt_with_mcp(self, prompt: str, mcp_context: MCPContext) -> str:
        """Enhance prompt with MCP context information"""
        context_info = mcp.format_for_llm(mcp_context)
        
        enhanced_prompt = f"""
[System Context]
{context_info}

[User Request]
{prompt}

[Instructions]
- Use the provided context to give more accurate and relevant responses
- If you need to use any tools, format your response as JSON with tool calls
- Consider the conversation history when formulating your response
"""
        return enhanced_prompt
