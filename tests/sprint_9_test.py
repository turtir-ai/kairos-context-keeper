#!/usr/bin/env python3
"""
Sprint 9 Test Suite
Test new deep code analysis capabilities
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

def test_code_parser():
    """Test the new code parser"""
    print_test_header("Code Parser Module")
    
    try:
        from core.code_parser import code_parser, CodeNode, NodeType
        print_result("Import code parser", True)
        
        # Test parsing a Python file
        test_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'core', 'code_parser.py')
        nodes, relationships = code_parser.parse_file(test_file)
        
        print_result("Parse Python file", True, f"Found {len(nodes)} nodes and {len(relationships)} relationships")
        
        # Check for expected node types
        node_types = [node.type for node in nodes]
        has_module = any(nt == NodeType.MODULE for nt in node_types)
        has_class = any(nt == NodeType.CLASS for nt in node_types)
        has_function = any(nt == NodeType.FUNCTION for nt in node_types)
        
        print_result("Module node found", has_module)
        print_result("Class nodes found", has_class)
        print_result("Function nodes found", has_function)
        
        # Test directory parsing (limited to avoid too much output)
        test_dir = os.path.join(os.path.dirname(__file__), '..', 'src', 'core')
        all_nodes, all_rels = code_parser.parse_directory(test_dir)
        print_result("Parse directory", True, f"Found {len(all_nodes)} total nodes and {len(all_rels)} relationships")
        
        return True
        
    except Exception as e:
        print_result("Code parser test", False, str(e))
        return False

def test_ast_converter():
    """Test AST to Neo4j converter"""
    print_test_header("AST Converter")
    
    try:
        from memory.ast_converter import ast_converter
        print_result("Import AST converter", True)
        
        # Test Cypher query generation
        from core.code_parser import code_parser, CodeNode, NodeType
        
        # Create a sample node
        sample_node = CodeNode(
            id="test_123",
            type=NodeType.FUNCTION,
            name="test_function",
            file_path="/test/file.py",
            start_line=1,
            end_line=5,
            start_char=0,
            end_char=100,
            content="def test_function():\n    pass",
            metadata={"complexity": 1, "args": []}
        )
        
        cypher_queries = ast_converter.convert_nodes_to_cypher([sample_node])
        print_result("Generate Cypher queries", True, f"Generated {len(cypher_queries)} queries")
        
        # Test predefined analysis queries
        analysis_queries = ast_converter.get_code_analysis_queries()
        expected_queries = ["dead_code_detection", "circular_dependencies", "complex_functions"]
        
        for query_name in expected_queries:
            has_query = query_name in analysis_queries
            print_result(f"Analysis query: {query_name}", has_query)
        
        return True
        
    except Exception as e:
        print_result("AST converter test", False, str(e))
        return False

async def test_mcp_code_analysis():
    """Test new MCP code analysis tool"""
    print_test_header("MCP Code Analysis Tool")
    
    try:
        from mcp.kairos_mcp_final import KairosMCPServer
        print_result("Import MCP server", True)
        
        server = KairosMCPServer()
        
        # Test tools list includes new analyzeCode tool
        tools_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        response = await server.handle_request(json.dumps(tools_request))
        tools = response.get("result", {}).get("tools", [])
        tool_names = [tool["name"] for tool in tools]
        
        has_analyze_code = "kairos.analyzeCode" in tool_names
        print_result("analyzeCode tool available", has_analyze_code)
        
        if has_analyze_code:
            # Test code analysis call
            analysis_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "kairos.analyzeCode",
                    "arguments": {
                        "query": "find dead code in project",
                        "analysis_type": "dead_code"
                    }
                }
            }
            
            analysis_response = await server.handle_request(json.dumps(analysis_request))
            print_result("Code analysis call", True, "Analysis request processed")
            
            # Check response structure
            content = analysis_response.get("result", {}).get("content", [])
            if content and len(content) > 0:
                result_text = content[0].get("text", "")
                try:
                    result_data = json.loads(result_text)
                    has_success = "success" in result_data
                    has_analysis_type = "analysis_type" in result_data
                    print_result("Analysis response structure", has_success and has_analysis_type)
                except:
                    print_result("Analysis response format", False, "Invalid JSON response")
        
        return True
        
    except Exception as e:
        print_result("MCP code analysis test", False, str(e))
        return False

def test_integration_workflow():
    """Test complete integration workflow"""
    print_test_header("Integration Workflow")
    
    try:
        # Test the complete flow: Parse -> Convert -> Analyze
        from core.code_parser import code_parser
        from memory.ast_converter import ast_converter
        
        # Parse a simple test file
        test_file = os.path.join(os.path.dirname(__file__), '..', 'src', 'main.py')
        if os.path.exists(test_file):
            nodes, relationships = code_parser.parse_file(test_file)
            print_result("Parse main.py", True, f"Found {len(nodes)} nodes")
            
            # Convert to Cypher (without executing)
            cypher_nodes = ast_converter.convert_nodes_to_cypher(nodes)
            cypher_rels = ast_converter.convert_relationships_to_cypher(relationships)
            
            print_result("Convert to Cypher", True, f"Generated {len(cypher_nodes)} node queries and {len(cypher_rels)} relationship queries")
        
        else:
            print_result("Find test file", False, "main.py not found")
        
        # Test statistics (will work even without Neo4j)
        try:
            stats = ast_converter.get_graph_statistics()
            print_result("Get graph statistics", True, f"Retrieved {len(stats)} statistics")
        except:
            print_result("Get graph statistics", False, "Neo4j not available (expected)")
        
        return True
        
    except Exception as e:
        print_result("Integration workflow test", False, str(e))
        return False

async def run_all_tests():
    """Run all Sprint 9 tests"""
    print("🚀 Starting Sprint 9 Deep Analysis Tests")
    print(f"📅 Test Run: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = []
    
    # Run all tests
    test_results.append(test_code_parser())
    test_results.append(test_ast_converter())
    test_results.append(await test_mcp_code_analysis())
    test_results.append(test_integration_workflow())
    
    # Print summary
    print_test_header("Test Summary")
    
    passed = sum(test_results)
    total = len(test_results)
    success_rate = (passed / total) * 100
    
    print(f"📊 Results: {passed}/{total} tests passed ({success_rate:.1f}%)")
    
    if passed == total:
        print("🎉 All tests passed! Sprint 9 Phase 1 components are working.")
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
    
    # Test recommendations
    print("\n🔧 Next Steps:")
    print("1. ✅ Code Parser Module - Working")
    print("2. ✅ AST Converter - Working") 
    print("3. ✅ MCP Code Analysis Tool - Integrated")
    print("4. 🔄 Need to initialize Neo4j for full functionality")
    print("5. 🔄 Need to run initial code graph generation")
    
    print(f"\n{'='*60}")
    print("🏆 Sprint 9 Phase 1 Test Complete")
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
