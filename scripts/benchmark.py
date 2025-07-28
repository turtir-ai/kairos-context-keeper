#!/usr/bin/env python3
"""
Performance benchmark script for Kairos
Tests various system components and measures performance
"""

import asyncio
import time
import statistics
import requests
import json
import sys
import os
from typing import Dict, List, Any
from pathlib import Path

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

class KairosBenchmark:
    """Benchmark suite for Kairos system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {}
        
    def print_header(self, test_name: str):
        """Print benchmark test header"""
        print(f"\n{'='*60}")
        print(f"🧪 {test_name}")
        print(f"{'='*60}")
    
    def benchmark_api_response_time(self, iterations: int = 100) -> Dict[str, float]:
        """Benchmark API response times"""
        self.print_header("API Response Time Benchmark")
        
        endpoints = [
            "/health",
            "/status", 
            "/api/monitoring/system-stats",
            "/agents/status",
            "/api/memory/stats"
        ]
        
        results = {}
        
        for endpoint in endpoints:
            print(f"\n📊 Testing {endpoint}...")
            times = []
            
            for i in range(iterations):
                start_time = time.time()
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    response_time = (time.time() - start_time) * 1000  # ms
                    
                    if response.status_code == 200:
                        times.append(response_time)
                    else:
                        print(f"  ⚠️  Status code: {response.status_code}")
                        
                except requests.RequestException as e:
                    print(f"  ❌ Request failed: {e}")
                    continue
                
                if (i + 1) % 20 == 0:
                    print(f"  Progress: {i + 1}/{iterations}")
            
            if times:
                avg_time = statistics.mean(times)
                median_time = statistics.median(times)
                min_time = min(times)
                max_time = max(times)
                
                results[endpoint] = {
                    "avg_ms": round(avg_time, 2),
                    "median_ms": round(median_time, 2),
                    "min_ms": round(min_time, 2),
                    "max_ms": round(max_time, 2),
                    "samples": len(times)
                }
                
                print(f"  ✅ Avg: {avg_time:.2f}ms, Median: {median_time:.2f}ms")
                print(f"     Min: {min_time:.2f}ms, Max: {max_time:.2f}ms")
            else:
                print(f"  ❌ No successful requests")
                results[endpoint] = {"error": "No successful requests"}
        
        return results
    
    def benchmark_concurrent_requests(self, concurrent_users: int = 10, requests_per_user: int = 10) -> Dict[str, Any]:
        """Benchmark concurrent request handling"""
        self.print_header("Concurrent Requests Benchmark")
        
        async def make_request_batch(session, endpoint: str, num_requests: int):
            """Make a batch of requests"""
            import aiohttp
            
            times = []
            for _ in range(num_requests):
                start_time = time.time()
                try:
                    async with session.get(f"{self.base_url}{endpoint}") as response:
                        await response.text()
                        response_time = (time.time() - start_time) * 1000
                        times.append(response_time)
                except Exception as e:
                    print(f"  ❌ Request failed: {e}")
            
            return times
        
        async def run_concurrent_test():
            import aiohttp
            
            endpoint = "/health"  # Use lightweight endpoint
            print(f"🚀 Testing {concurrent_users} concurrent users, {requests_per_user} requests each")
            
            async with aiohttp.ClientSession() as session:
                start_time = time.time()
                
                # Create tasks for concurrent users
                tasks = [
                    make_request_batch(session, endpoint, requests_per_user)
                    for _ in range(concurrent_users)
                ]
                
                # Run all tasks concurrently
                results = await asyncio.gather(*tasks)
                
                total_time = time.time() - start_time
                
                # Aggregate results
                all_times = []
                for user_times in results:
                    all_times.extend(user_times)
                
                if all_times:
                    total_requests = len(all_times)
                    avg_response_time = statistics.mean(all_times)
                    requests_per_second = total_requests / total_time
                    
                    return {
                        "concurrent_users": concurrent_users,
                        "requests_per_user": requests_per_user,
                        "total_requests": total_requests,
                        "total_time_seconds": round(total_time, 2),
                        "avg_response_time_ms": round(avg_response_time, 2),
                        "requests_per_second": round(requests_per_second, 2),
                        "successful_requests": total_requests
                    }
                else:
                    return {"error": "No successful requests"}
        
        try:
            import aiohttp
            return asyncio.run(run_concurrent_test())
        except ImportError:
            print("❌ aiohttp not available for concurrent testing")
            return {"error": "aiohttp not available"}
    
    def benchmark_memory_operations(self, iterations: int = 50) -> Dict[str, Any]:
        """Benchmark memory system operations"""
        self.print_header("Memory Operations Benchmark")
        
        # Test memory query endpoint
        print("🧠 Testing memory query operations...")
        
        queries = [
            "system",
            "agents", 
            "memory",
            "tasks",
            "*"
        ]
        
        results = {}
        
        for query in queries:
            print(f"  Testing query: '{query}'")
            times = []
            
            for _ in range(iterations):
                start_time = time.time()
                try:
                    response = requests.get(
                        f"{self.base_url}/api/memory/query",
                        params={"query": query, "limit": 10},
                        timeout=10
                    )
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        times.append(response_time)
                        data = response.json()
                        # Could analyze response data here
                    
                except requests.RequestException:
                    continue
            
            if times:
                results[query] = {
                    "avg_ms": round(statistics.mean(times), 2),
                    "min_ms": round(min(times), 2),
                    "max_ms": round(max(times), 2),
                    "samples": len(times)
                }
                print(f"    ✅ Avg: {results[query]['avg_ms']}ms")
            else:
                results[query] = {"error": "No successful requests"}
        
        return results
    
    def benchmark_agent_operations(self, iterations: int = 20) -> Dict[str, Any]:
        """Benchmark agent coordination operations"""
        self.print_header("Agent Operations Benchmark")
        
        print("🤖 Testing agent task creation and execution...")
        
        task_types = [
            {"type": "research", "description": "Test research task"},
            {"type": "analysis", "description": "Test analysis task"},
            {"type": "monitoring", "description": "Test monitoring task"}
        ]
        
        results = {}
        
        for task_spec in task_types:
            task_type = task_spec["type"]
            print(f"  Testing {task_type} tasks...")
            
            creation_times = []
            execution_times = []
            
            for _ in range(iterations):
                # Test task creation
                start_time = time.time()
                try:
                    response = requests.post(
                        f"{self.base_url}/api/orchestration/tasks",
                        json=task_spec,
                        timeout=10
                    )
                    creation_time = (time.time() - start_time) * 1000
                    
                    if response.status_code == 200:
                        creation_times.append(creation_time)
                        
                        # Try to execute the task if we got a task_id
                        task_data = response.json()
                        if task_data.get("success") and task_data.get("task_id"):
                            exec_start = time.time()
                            exec_response = requests.post(
                                f"{self.base_url}/api/orchestration/tasks/{task_data['task_id']}/execute",
                                timeout=30
                            )
                            execution_time = (time.time() - exec_start) * 1000
                            
                            if exec_response.status_code == 200:
                                execution_times.append(execution_time)
                
                except requests.RequestException:
                    continue
            
            task_results = {}
            
            if creation_times:
                task_results["creation"] = {
                    "avg_ms": round(statistics.mean(creation_times), 2),
                    "samples": len(creation_times)
                }
            
            if execution_times:
                task_results["execution"] = {
                    "avg_ms": round(statistics.mean(execution_times), 2),
                    "samples": len(execution_times)
                }
            
            results[task_type] = task_results
            
            if creation_times:
                print(f"    ✅ Creation avg: {task_results['creation']['avg_ms']}ms")
            if execution_times:
                print(f"    ✅ Execution avg: {task_results['execution']['avg_ms']}ms")
        
        return results
    
    def run_full_benchmark(self) -> Dict[str, Any]:
        """Run complete benchmark suite"""
        print("🌌 Kairos Performance Benchmark Suite")
        print(f"🎯 Target: {self.base_url}")
        print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check if service is available
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code != 200:
                print(f"❌ Service not available (status: {response.status_code})")
                return {"error": "Service not available"}
        except requests.RequestException as e:
            print(f"❌ Cannot connect to service: {e}")
            return {"error": f"Cannot connect: {e}"}
        
        print("✅ Service is available, starting benchmarks...")
        
        benchmark_start = time.time()
        
        # Run benchmarks
        self.results = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "target_url": self.base_url,
            "api_response_times": self.benchmark_api_response_time(50),
            "concurrent_requests": self.benchmark_concurrent_requests(5, 10),
            "memory_operations": self.benchmark_memory_operations(20),
            "agent_operations": self.benchmark_agent_operations(10)
        }
        
        total_time = time.time() - benchmark_start
        self.results["total_benchmark_time_seconds"] = round(total_time, 2)
        
        # Print summary
        self.print_summary()
        
        return self.results
    
    def print_summary(self):
        """Print benchmark summary"""
        print(f"\n{'='*60}")
        print("📊 BENCHMARK SUMMARY")
        print(f"{'='*60}")
        
        if "api_response_times" in self.results:
            print("\n🌐 API Response Times:")
            for endpoint, data in self.results["api_response_times"].items():
                if "avg_ms" in data:
                    print(f"  {endpoint}: {data['avg_ms']}ms avg")
        
        if "concurrent_requests" in self.results:
            concurrent = self.results["concurrent_requests"]
            if "requests_per_second" in concurrent:
                print(f"\n🚀 Concurrent Performance:")
                print(f"  Requests/second: {concurrent['requests_per_second']}")
                print(f"  Avg response time: {concurrent['avg_response_time_ms']}ms")
        
        if "memory_operations" in self.results:
            print(f"\n🧠 Memory Operations:")
            for query, data in self.results["memory_operations"].items():
                if "avg_ms" in data:
                    print(f"  Query '{query}': {data['avg_ms']}ms avg")
        
        if "agent_operations" in self.results:
            print(f"\n🤖 Agent Operations:")
            for task_type, data in self.results["agent_operations"].items():
                if "creation" in data:
                    print(f"  {task_type} creation: {data['creation']['avg_ms']}ms")
                if "execution" in data:
                    print(f"  {task_type} execution: {data['execution']['avg_ms']}ms")
        
        print(f"\n⏱️  Total benchmark time: {self.results['total_benchmark_time_seconds']}s")
        print(f"✅ Benchmark completed!")
    
    def save_results(self, filename: str = None):
        """Save benchmark results to file"""
        if not filename:
            timestamp = time.strftime('%Y%m%d_%H%M%S')
            filename = f"benchmark_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"💾 Results saved to: {filename}")

def main():
    """Main benchmark function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kairos Performance Benchmark")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL for Kairos API")
    parser.add_argument("--save", action="store_true", help="Save results to file")
    parser.add_argument("--output", help="Output filename for results")
    
    args = parser.parse_args()
    
    benchmark = KairosBenchmark(args.url)
    results = benchmark.run_full_benchmark()
    
    if args.save:
        benchmark.save_results(args.output)
    
    return 0 if "error" not in results else 1

if __name__ == "__main__":
    sys.exit(main())
