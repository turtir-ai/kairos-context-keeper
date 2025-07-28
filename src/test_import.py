#!/usr/bin/env python3
"""Test script to verify imports work correctly in both execution modes"""

import sys
import os

print("Testing import methods...")
print(f"Current directory: {os.getcwd()}")
print(f"Script location: {os.path.abspath(__file__)}")
print(f"Python path: {sys.path[:3]}...")  # Show first 3 paths

# Test 1: Try relative imports (will fail when run directly)
print("\n--- Test 1: Relative imports ---")
try:
    from .api.websocket_manager import WebSocketManager
    print("✓ Relative import successful (running as module)")
except ImportError as e:
    print(f"✗ Relative import failed: {e}")
    print("  This is expected when running directly")

# Test 2: Try absolute imports after adding to path
print("\n--- Test 2: Absolute imports with sys.path ---")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from api.websocket_manager import WebSocketManager
    print("✓ Absolute import successful")
    print(f"  WebSocketManager imported: {WebSocketManager}")
except ImportError as e:
    print(f"✗ Absolute import failed: {e}")

# Test 3: Test the combined approach
print("\n--- Test 3: Combined approach (try/except) ---")
try:
    from .orchestration.agent_coordinator import agent_coordinator
    print("✓ Relative import of agent_coordinator successful")
except ImportError:
    try:
        from orchestration.agent_coordinator import agent_coordinator
        print("✓ Absolute import of agent_coordinator successful")
    except ImportError as e:
        print(f"✗ Both import methods failed: {e}")

print("\n--- Results ---")
print("The combined try/except approach should work in both scenarios:")
print("1. When running as module: python -m src.test_import")
print("2. When running directly: python src/test_import.py")
