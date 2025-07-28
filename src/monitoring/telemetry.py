"""
OpenTelemetry Integration for Kairos
Provides distributed tracing and metrics collection
"""

import os
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from contextlib import contextmanager

from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.trace import Status, StatusCode
from opentelemetry.metrics import CallbackOptions, Observation

class TelemetryManager:
    """Manages OpenTelemetry configuration and instrumentation"""
    
    def __init__(self, service_name: str = "kairos", environment: str = "development"):
        self.logger = logging.getLogger(__name__)
        self.service_name = service_name
        self.environment = environment
        self.tracer = None
        self.meter = None
        self._initialized = False
        
        # OTLP endpoint configuration
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "localhost:4317")
        self.otlp_headers = os.getenv("OTLP_HEADERS", "")
        
    def initialize(self):
        """Initialize OpenTelemetry providers and instrumentations"""
        if self._initialized:
            self.logger.warning("Telemetry already initialized")
            return
            
        try:
            # Create resource
            resource = Resource.create({
                "service.name": self.service_name,
                "service.version": "1.0.0",
                "deployment.environment": self.environment,
                "service.namespace": "kairos",
            })
            
            # Setup tracing
            self._setup_tracing(resource)
            
            # Setup metrics
            self._setup_metrics(resource)
            
            # Setup automatic instrumentation
            self._setup_instrumentation()
            
            self._initialized = True
            self.logger.info(f"🔭 OpenTelemetry initialized for {self.service_name}")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize telemetry: {e}")
            
    def _setup_tracing(self, resource: Resource):
        """Setup distributed tracing"""
        # Create OTLP trace exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=self.otlp_endpoint,
            headers=self._parse_headers(),
            insecure=True  # For development
        )
        
        # Create tracer provider
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(otlp_exporter)
        provider.add_span_processor(processor)
        
        # Set global tracer provider
        trace.set_tracer_provider(provider)
        self.tracer = trace.get_tracer(self.service_name)
        
    def _setup_metrics(self, resource: Resource):
        """Setup metrics collection"""
        # Create OTLP metric exporter
        otlp_exporter = OTLPMetricExporter(
            endpoint=self.otlp_endpoint,
            headers=self._parse_headers(),
            insecure=True  # For development
        )
        
        # Create metric reader
        metric_reader = PeriodicExportingMetricReader(
            exporter=otlp_exporter,
            export_interval_millis=60000  # Export every minute
        )
        
        # Create meter provider
        provider = MeterProvider(
            resource=resource,
            metric_readers=[metric_reader]
        )
        
        # Set global meter provider
        metrics.set_meter_provider(provider)
        self.meter = metrics.get_meter(self.service_name)
        
        # Create default metrics
        self._create_default_metrics()
        
    def _setup_instrumentation(self):
        """Setup automatic instrumentation for common libraries"""
        # FastAPI
        FastAPIInstrumentor.instrument(tracer_provider=trace.get_tracer_provider())
        
        # Redis
        RedisInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())
        
        # PostgreSQL
        Psycopg2Instrumentor().instrument(tracer_provider=trace.get_tracer_provider())
        
        # HTTP clients
        RequestsInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())
        AioHttpClientInstrumentor().instrument(tracer_provider=trace.get_tracer_provider())
        
    def _create_default_metrics(self):
        """Create default application metrics"""
        # Request counter
        self.request_counter = self.meter.create_counter(
            name="kairos_requests_total",
            description="Total number of requests",
            unit="1"
        )
        
        # Response time histogram
        self.response_time_histogram = self.meter.create_histogram(
            name="kairos_response_time",
            description="Response time in milliseconds",
            unit="ms"
        )
        
        # Active connections gauge
        self.active_connections = self.meter.create_up_down_counter(
            name="kairos_active_connections",
            description="Number of active connections",
            unit="1"
        )
        
        # Error counter
        self.error_counter = self.meter.create_counter(
            name="kairos_errors_total",
            description="Total number of errors",
            unit="1"
        )
        
        # LLM token usage
        self.llm_token_counter = self.meter.create_counter(
            name="kairos_llm_tokens_total",
            description="Total LLM tokens used",
            unit="1"
        )
        
        # Memory usage gauge (callback-based)
        self.meter.create_observable_gauge(
            name="kairos_memory_usage_bytes",
            callbacks=[self._get_memory_usage],
            description="Current memory usage in bytes",
            unit="By"
        )
        
    def _get_memory_usage(self, options: CallbackOptions) -> Observation:
        """Callback for memory usage metric"""
        import psutil
        process = psutil.Process()
        memory_bytes = process.memory_info().rss
        return [Observation(memory_bytes)]
        
    def _parse_headers(self) -> Dict[str, str]:
        """Parse OTLP headers from environment variable"""
        if not self.otlp_headers:
            return {}
            
        headers = {}
        for header in self.otlp_headers.split(","):
            if "=" in header:
                key, value = header.split("=", 1)
                headers[key.strip()] = value.strip()
        return headers
        
    @contextmanager
    def trace_span(self, name: str, attributes: Dict[str, Any] = None):
        """Context manager for creating trace spans"""
        if not self.tracer:
            yield None
            return
            
        with self.tracer.start_as_current_span(name) as span:
            if attributes:
                span.set_attributes(attributes)
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise
                
    def trace_function(self, name: str = None):
        """Decorator for tracing functions"""
        def decorator(func: Callable):
            span_name = name or f"{func.__module__}.{func.__name__}"
            
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with self.trace_span(span_name):
                    return await func(*args, **kwargs)
                    
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with self.trace_span(span_name):
                    return func(*args, **kwargs)
                    
            return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
        return decorator
        
    def record_metric(self, metric_name: str, value: float, attributes: Dict[str, str] = None):
        """Record a metric value"""
        if not self.meter:
            return
            
        attrs = attributes or {}
        
        if metric_name == "request_count":
            self.request_counter.add(value, attrs)
        elif metric_name == "response_time":
            self.response_time_histogram.record(value, attrs)
        elif metric_name == "active_connections":
            self.active_connections.add(value, attrs)
        elif metric_name == "error_count":
            self.error_counter.add(value, attrs)
        elif metric_name == "llm_tokens":
            self.llm_token_counter.add(value, attrs)
            
    def get_tracer(self) -> Optional[trace.Tracer]:
        """Get the configured tracer"""
        return self.tracer
        
    def get_meter(self) -> Optional[metrics.Meter]:
        """Get the configured meter"""
        return self.meter
        
    def shutdown(self):
        """Shutdown telemetry providers"""
        if self._initialized:
            # Shutdown tracer provider
            if trace.get_tracer_provider():
                trace.get_tracer_provider().shutdown()
                
            # Shutdown meter provider
            if metrics.get_meter_provider():
                metrics.get_meter_provider().shutdown()
                
            self._initialized = False
            self.logger.info("🛑 OpenTelemetry shutdown complete")

# Global telemetry instance
telemetry_manager = TelemetryManager()

# Convenience decorators
def trace_span(name: str = None, attributes: Dict[str, Any] = None):
    """Decorator for tracing with spans"""
    def decorator(func):
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with telemetry_manager.trace_span(span_name, attributes):
                return await func(*args, **kwargs)
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with telemetry_manager.trace_span(span_name, attributes):
                return func(*args, **kwargs)
                
        import asyncio
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# Example usage in agents
class TelemetryEnabledAgent:
    """Base class for agents with telemetry support"""
    
    def __init__(self, agent_type: str):
        self.agent_type = agent_type
        self.telemetry = telemetry_manager
        
    @trace_span(attributes={"agent.type": "research"})
    async def process_with_telemetry(self, task: Dict[str, Any]):
        """Example method with automatic tracing"""
        # Record metric
        self.telemetry.record_metric("request_count", 1, {"agent": self.agent_type})
        
        # Process task
        result = await self._process_internal(task)
        
        # Record response time
        self.telemetry.record_metric("response_time", result.get("duration_ms", 0))
        
        return result
