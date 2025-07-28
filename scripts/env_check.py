#!/usr/bin/env python3
"""
Environment checker for Kairos
Validates that all required dependencies and services are available
"""

import sys
import subprocess
import importlib
import socket
import os
from pathlib import Path
from typing import List, Dict, Tuple

def check_python_version() -> Tuple[bool, str]:
    """Check if Python version is compatible"""
    min_version = (3, 11)
    current = sys.version_info[:2]
    
    if current >= min_version:
        return True, f"✅ Python {current[0]}.{current[1]} (compatible)"
    else:
        return False, f"❌ Python {current[0]}.{current[1]} (need >= {min_version[0]}.{min_version[1]})"

def check_required_packages() -> List[Tuple[bool, str]]:
    """Check if required Python packages are available"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'httpx',
        'asyncpg',
        'redis',
        'neo4j',
        'qdrant_client',
        'torch',
        'transformers',
        'sentence_transformers',
        'toml',
        'psutil',
        'aiofiles',
    ]
    
    results = []
    for package in required_packages:
        try:
            importlib.import_module(package.replace('-', '_'))
            results.append((True, f"✅ {package}"))
        except ImportError:
            results.append((False, f"❌ {package} (not installed)"))
    
    return results

def check_port(host: str, port: int, timeout: int = 3) -> bool:
    """Check if a port is accessible"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.error, socket.timeout):
        return False

def check_external_services() -> List[Tuple[bool, str]]:
    """Check if external services are accessible"""
    services = [
        ('PostgreSQL', 'localhost', 5432),
        ('Redis', 'localhost', 6379),
        ('Neo4j', 'localhost', 7687),
        ('Qdrant', 'localhost', 6333),
        ('Ollama', 'localhost', 11434),
    ]
    
    results = []
    for service, host, port in services:
        if check_port(host, port):
            results.append((True, f"✅ {service} ({host}:{port})"))
        else:
            results.append((False, f"❌ {service} ({host}:{port}) - not accessible"))
    
    return results

def main():
    """Run all environment checks"""
    print("🌌 Kairos Environment Check")
    print("=" * 50)
    
    all_passed = True
    
    # Python version
    print("\n📍 Python Version:")
    passed, msg = check_python_version()
    print(f"  {msg}")
    if not passed:
        all_passed = False
    
    # Required packages
    print("\n📦 Required Python Packages:")
    package_results = check_required_packages()
    for passed, msg in package_results:
        print(f"  {msg}")
        if not passed:
            all_passed = False
    
    # External services
    print("\n🌐 External Services:")
    service_results = check_external_services()
    for passed, msg in service_results:
        print(f"  {msg}")
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ Environment check PASSED!")
        print("🚀 Kairos is ready to run!")
    else:
        print("⚠️  Environment check found issues!")
        print("🔧 Please resolve the issues marked with ❌")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
