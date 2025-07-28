"""
Weather Plugin - Example plugin for Kairos
"""

import aiohttp
import json
from typing import Dict, Any, List
from datetime import datetime

from .base_plugin import BasePlugin, PluginMetadata, PluginCapability

class WeatherPlugin(BasePlugin):
    """Plugin for fetching weather information"""
    
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="weather",
            version="1.0.0",
            author="Kairos Team",
            description="Provides weather information for any location",
            capabilities=[
                PluginCapability(
                    name="get_weather",
                    description="Get current weather for a location",
                    parameters={
                        "location": {
                            "type": "string",
                            "description": "City name or coordinates",
                            "required": True
                        },
                        "units": {
                            "type": "string",
                            "description": "Temperature units (metric/imperial)",
                            "required": False,
                            "default": "metric"
                        }
                    },
                    required_permissions=["internet_access"]
                ),
                PluginCapability(
                    name="get_forecast",
                    description="Get weather forecast for upcoming days",
                    parameters={
                        "location": {
                            "type": "string",
                            "description": "City name or coordinates",
                            "required": True
                        },
                        "days": {
                            "type": "integer",
                            "description": "Number of days to forecast",
                            "required": False,
                            "default": 5
                        }
                    },
                    required_permissions=["internet_access"]
                )
            ],
            dependencies=["aiohttp"],
            config_schema={
                "api_key": {
                    "type": "string",
                    "description": "OpenWeatherMap API key",
                    "required": False
                },
                "api_url": {
                    "type": "string",
                    "description": "Weather API base URL",
                    "required": False,
                    "default": "https://api.openweathermap.org/data/2.5"
                }
            }
        )
    
    async def initialize(self) -> bool:
        """Initialize the weather plugin"""
        try:
            # Use a mock API for demonstration
            self.api_url = self.config.get("api_url", "https://api.openweathermap.org/data/2.5")
            self.api_key = self.config.get("api_key", "demo_key")
            
            # Create aiohttp session
            self.session = aiohttp.ClientSession()
            
            self.logger.info("Weather plugin initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize weather plugin: {e}")
            return False
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute weather-related tasks"""
        action = task.get("action")
        parameters = task.get("parameters", {})
        
        try:
            if action == "get_weather":
                return await self._get_current_weather(parameters)
            elif action == "get_forecast":
                return await self._get_weather_forecast(parameters)
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            self.logger.error(f"Weather plugin execution failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_current_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get current weather (mock implementation)"""
        location = params.get("location")
        if not location:
            return {
                "success": False,
                "error": "Location parameter is required"
            }
        
        # Mock weather data for demonstration
        mock_weather = {
            "location": location,
            "temperature": 22.5,
            "feels_like": 21.0,
            "humidity": 65,
            "description": "Partly cloudy",
            "wind_speed": 12.5,
            "wind_direction": "NW",
            "pressure": 1013,
            "timestamp": datetime.now().isoformat()
        }
        
        return {
            "success": True,
            "result": mock_weather
        }
    
    async def _get_weather_forecast(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get weather forecast (mock implementation)"""
        location = params.get("location")
        days = params.get("days", 5)
        
        if not location:
            return {
                "success": False,
                "error": "Location parameter is required"
            }
        
        # Mock forecast data
        forecast = []
        for i in range(days):
            forecast.append({
                "day": i + 1,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "high": 25 + i,
                "low": 15 + i,
                "description": ["Sunny", "Partly cloudy", "Cloudy", "Rainy", "Clear"][i % 5],
                "precipitation_chance": (i * 20) % 100
            })
        
        return {
            "success": True,
            "result": {
                "location": location,
                "forecast": forecast
            }
        }
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if hasattr(self, 'session'):
            await self.session.close()
        self.logger.info("Weather plugin cleaned up")
