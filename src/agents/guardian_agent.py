import logging
import re
import ast
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
from src.agents.base_agent import BaseAgent
from src.llm_router import LLMRouter

# Import MCP for context management
try:
    from ..mcp.model_context_protocol import MCPContext
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False

class GuardianAgent(BaseAgent):
    """Agent responsible for validating outputs and ensuring compliance with project rules"""
    
    def __init__(self, mcp_context: Optional['MCPContext'] = None):
        super().__init__("GuardianAgent", mcp_context)
        self.logger = logging.getLogger(__name__)
        self.llm_router = LLMRouter()
        
        # Load project constitution
        self.constitution = self._load_constitution()
        
        # Project validation rules
        self.validation_rules = {
            "code_quality": {
                "required_patterns": [r"def\s+\w+\(.*\):", r"class\s+\w+.*:"],
                "forbidden_patterns": [r"print\(.*\)", r"import.*\*"],
                "description": "Check for proper Python coding patterns"
            },
            "security": {
                "forbidden_patterns": [r"eval\(", r"exec\(", r"__import__"],
                "description": "Check for potentially unsafe code patterns"
            },
            "consistency": {
                "required_headers": ["TODO", "FIXME", "NOTE"],
                "description": "Ensure consistent documentation and comments"
            }
        }
        
    def guard(self, output: str, context: Dict = None) -> Dict[str, Any]:
        """Validate output against project rules and standards"""
        self.logger.info(f"🛡️ Validating output of length: {len(output)}")
        print(f"🛡️ Validating output...")
        
        validation_results = {
            "passed": True,
            "violations": [],
            "score": 100,
            "validated_at": datetime.now().isoformat(),
            "agent": self.name,
            "output_length": len(output),
            "context_used": context is not None,
            "mcp_context_available": self.mcp_context is not None
        }
        
        # Add MCP context information if available
        if self.mcp_context:
            validation_results["project_id"] = self.mcp_context.project_id
            validation_results["session_id"] = self.mcp_context.session_id
            
            # Update MCP context with validation start
            self.mcp_context.local_context['current_validation'] = {
                'output_length': len(output),
                'started_at': datetime.now().isoformat(),
                'context_provided': context is not None
            }
        
        # Run validation rules
        for rule_name, rule_config in self.validation_rules.items():
            rule_result = self._validate_rule(output, rule_name, rule_config)
            
            if not rule_result["passed"]:
                validation_results["passed"] = False
                validation_results["violations"].extend(rule_result["violations"])
                validation_results["score"] -= rule_result["penalty"]
        
        # Log results
        if validation_results["passed"]:
            self.logger.info("✅ Validation passed")
            print("✅ Validation passed")
        else:
            self.logger.warning(f"⚠️ Validation failed with {len(validation_results['violations'])} violations")
            print(f"⚠️ Validation failed with {len(validation_results['violations'])} violations")
            
        return validation_results
        
    def _validate_rule(self, output: str, rule_name: str, rule_config: Dict) -> Dict[str, Any]:
        """Validate a specific rule against the output"""
        violations = []
        penalty = 0
        
        # Check forbidden patterns
        if "forbidden_patterns" in rule_config:
            for pattern in rule_config["forbidden_patterns"]:
                matches = re.findall(pattern, output, re.IGNORECASE)
                if matches:
                    violations.append({
                        "rule": rule_name,
                        "type": "forbidden_pattern",
                        "pattern": pattern,
                        "matches": len(matches),
                        "description": f"Found forbidden pattern: {pattern}"
                    })
                    penalty += 10 * len(matches)
        
        # Check required patterns
        if "required_patterns" in rule_config:
            for pattern in rule_config["required_patterns"]:
                if not re.search(pattern, output, re.IGNORECASE):
                    violations.append({
                        "rule": rule_name,
                        "type": "missing_pattern", 
                        "pattern": pattern,
                        "description": f"Missing required pattern: {pattern}"
                    })
                    penalty += 15
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "penalty": penalty
        }
        
    def add_validation_rule(self, rule_name: str, rule_config: Dict):
        """Add a new validation rule"""
        self.validation_rules[rule_name] = rule_config
        self.logger.info(f"Added validation rule: {rule_name}")
        
    def _load_constitution(self) -> Dict[str, Any]:
        """Load project constitution from steering document"""
        constitution = {
            "principles": [
                "Maintain context across all interactions",
                "Use autonomous agents for specialized tasks",
                "Ensure code quality and security",
                "Enable continuous learning and adaptation"
            ],
            "coding_standards": {
                "python": {
                    "style": "PEP 8",
                    "docstrings": "Google style",
                    "type_hints": "Required for public methods",
                    "max_line_length": 100,
                    "forbidden_imports": ["from X import *", "import os.system"]
                }
            },
            "security_rules": [
                "No hardcoded credentials",
                "No eval() or exec() usage",
                "Validate all external inputs",
                "Use environment variables for secrets"
            ]
        }
        
        # Try to load from steering.md if it exists
        steering_path = Path(".kiro/steering.md")
        if steering_path.exists():
            try:
                with open(steering_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Extract constitution sections (simplified)
                    if "## Constitution" in content:
                        constitution["from_steering"] = True
            except Exception as e:
                self.logger.warning(f"Could not load steering.md: {e}")
                
        return constitution
    
    async def validate_code_with_static_analysis(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Run static code analysis using external tools"""
        if language != "python":
            return {"error": "Only Python analysis supported currently"}
            
        results = {
            "syntax_valid": True,
            "style_issues": [],
            "security_issues": [],
            "complexity_score": 0
        }
        
        # Check syntax with AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            results["syntax_valid"] = False
            results["syntax_error"] = str(e)
            return results
            
        # Run pylint if available
        try:
            # Save code to temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(code)
                temp_path = f.name
                
            # Run pylint
            result = subprocess.run(
                ["pylint", "--output-format=json", temp_path],
                capture_output=True,
                text=True
            )
            
            if result.stdout:
                pylint_results = json.loads(result.stdout)
                for issue in pylint_results:
                    if issue["type"] in ["error", "warning"]:
                        results["style_issues"].append({
                            "line": issue.get("line"),
                            "type": issue.get("type"),
                            "message": issue.get("message")
                        })
                        
            # Clean up
            os.unlink(temp_path)
            
        except Exception as e:
            self.logger.warning(f"Pylint analysis failed: {e}")
            
        return results
    
    async def validate_with_llm(self, content: str, validation_type: str = "general") -> Dict[str, Any]:
        """Use LLM for semantic validation"""
        prompts = {
            "general": f"""Analyze this content for quality, clarity, and best practices:

{content[:1000]}

Provide:
1. Quality score (0-100)
2. Key issues found
3. Improvement suggestions""",
            
            "security": f"""Analyze this code for security vulnerabilities:

{content[:1000]}

Check for:
1. SQL injection risks
2. XSS vulnerabilities
3. Insecure data handling
4. Authentication issues""",
            
            "architecture": f"""Analyze this code for architectural issues:

{content[:1000]}

Check for:
1. SOLID principle violations
2. Code coupling issues
3. Maintainability concerns
4. Design pattern misuse"""
        }
        
        prompt = prompts.get(validation_type, prompts["general"])
        
        try:
            response = await self.llm_router.generate(prompt)
            return {
                "validation_type": validation_type,
                "llm_analysis": response.get("response", "Analysis failed"),
                "model_used": response.get("model", "unknown")
            }
        except Exception as e:
            self.logger.error(f"LLM validation failed: {e}")
            return {"error": str(e)}
        
    def get_status(self):
        return {
            "name": self.name,
            "status": self.status,
            "validation_rules": list(self.validation_rules.keys()),
            "constitution_loaded": bool(self.constitution),
            "last_activity": datetime.now().isoformat()
        }
