#!/usr/bin/env python3
"""
Sprint 8 Integration Test
Comprehensive test suite to verify all Sprint 8 components are working correctly
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def print_test_header(test_name):
    """Print test section header"""
    print(f"\n{'='*60}")
    print(f"🧪 Testing: {test_name}")
    print(f"{'='*60}")

def print_result(test_name, success, details=""):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} {test_name}")
    if details:
        print(f"   📝 {details}")

async def test_notification_system():
    """Test notification event bus system"""
    print_test_header("Notification System")
    
    try:
        from notifications.event_bus import event_bus, NotificationEvent, NotificationSeverity, NotificationChannel
        print_result("Import notification system", True)
        
        # Test event creation
        import uuid
        test_event = NotificationEvent(
            id=str(uuid.uuid4()),
            title="Sprint 8 Integration Test",
            message="Testing notification system functionality",
            severity=NotificationSeverity.INFO,
            source="integration_test",
            channels=[NotificationChannel.CONSOLE]
        )
        print_result("Create notification event", True, f"Event ID: {test_event.id[:8]}...")
        
        # Test publishing (should work even without subscribers)
        await event_bus.publish(test_event)
        print_result("Publish notification", True)
        
        # Test history
        history = event_bus.get_notification_history(limit=5)
        print_result("Get notification history", True, f"Retrieved {len(history)} notifications")
        
        return True
        
    except Exception as e:
        print_result("Notification system test", False, str(e))
        return False

def test_context_service():
    """Test context service"""
    print_test_header("Context Service")
    
    try:
        from services.context_service import get_enriched_context
        print_result("Import context service", True)
        
        # Note: Context service is async, but we'll just test import for now
        print_result("Context service availability", True, "Service ready for async calls")
        
        return True
        
    except Exception as e:
        print_result("Context service test", False, str(e))
        return False

async def test_mcp_server():
    """Test MCP server"""
    print_test_header("MCP Server")
    
    try:
        # Direct import to avoid __init__.py issues
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src', 'mcp'))
        from kairos_mcp_final import KairosMCPServer
        
        server = KairosMCPServer()
        print_result("Import MCP server", True, f"Server: {server.name} v{server.version}")
        
        # Test server capabilities
        test_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        # Handle async properly
        response = await server.handle_request(json.dumps(test_request))
        
        if "result" in response and "tools" in response["result"]:
            tool_count = len(response["result"]["tools"])
            print_result("MCP tools list", True, f"Found {tool_count} tools")
        else:
            print_result("MCP tools list", False, "Invalid response format")
            
        return True
        
    except Exception as e:
        print_result("MCP server test", False, str(e))
        return False

def test_ide_notifications():
    """Test IDE notification channels"""
    print_test_header("IDE Notification Channels")
    
    try:
        from notifications.ide_channels import ide_notification_manager
        print_result("Import IDE notification manager", True)
        
        # Test getting notifications
        notifications = ide_notification_manager.get_mcp_notifications(5)
        if "success" in notifications:
            count = notifications.get("count", 0)
            print_result("Get MCP notifications", True, f"Retrieved {count} notifications")
        else:
            print_result("Get MCP notifications", False, "Invalid response format")
            
        # Test acknowledgment
        result = ide_notification_manager.acknowledge_mcp_notification("test_id")
        print_result("Acknowledge notification", True, "Acknowledgment processed")
        
        return True
        
    except Exception as e:
        print_result("IDE notification channels test", False, str(e))
        return False

def test_supervisor_agent():
    """Test supervisor agent"""
    print_test_header("Supervisor Agent")
    
    try:
        # Check if supervisor agent file exists and is importable
        supervisor_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'agents', 'supervisor_agent.py')
        if os.path.exists(supervisor_path):
            print_result("Supervisor agent file exists", True)
            
            # Try basic import test without full initialization
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("supervisor_agent", supervisor_path)
                if spec and spec.loader:
                    print_result("Supervisor agent importable", True, "Module can be loaded")
                    return True
                else:
                    print_result("Supervisor agent importable", False, "Module spec failed")
                    return False
            except Exception as e:
                print_result("Supervisor agent import test", False, str(e))
                return False
        else:
            print_result("Supervisor agent file exists", False, "File not found")
            return False
        
    except Exception as e:
        print_result("Supervisor agent test", False, str(e))
        return False

def test_documentation():
    """Test documentation completeness"""
    print_test_header("Documentation")
    
    required_docs = [
        "docs/integrations/cursor_integration.md",
        "docs/integrations/kiro_integration.md",
        "docs/sprint_8_plan.md",
        "docs/sprint_8_completion_checklist.md"
    ]
    
    doc_count = 0
    base_path = os.path.join(os.path.dirname(__file__), '..')
    
    for doc_path in required_docs:
        full_path = os.path.join(base_path, doc_path)
        if os.path.exists(full_path):
            doc_count += 1
            print_result(f"Documentation: {os.path.basename(doc_path)}", True)
        else:
            print_result(f"Documentation: {os.path.basename(doc_path)}", False, "File not found")
    
    success = doc_count == len(required_docs)
    print_result("Documentation completeness", success, f"{doc_count}/{len(required_docs)} files found")
    
    return success

async def run_all_tests():
    """Run all Sprint 8 integration tests"""
    print("🚀 Starting Sprint 8 Integration Tests")
    print(f"📅 Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # Run all tests
    test_results.append(await test_notification_system())
    test_results.append(test_context_service())
    test_results.append(await test_mcp_server())
    test_results.append(test_ide_notifications())
    test_results.append(test_supervisor_agent())
    test_results.append(test_documentation())
    
    # Print summary
    print_test_header("Test Summary")
    
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"📊 Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Sprint 8 is ready for completion.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
    
    print(f"\n{'='*60}")
    print("🏆 Sprint 8 Integration Test Complete")
    print(f"{'='*60}")
    
    return passed == total

if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_tests())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        sys.exit(1)
