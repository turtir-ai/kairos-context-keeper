# Cursor IDE Integration Guide

## 🎯 Kairos + Cursor: AI-Enhanced Development

This guide will help you integrate Kairos MCP Server with Cursor IDE to unlock **context-aware AI assistance** for your development workflow.

## 📋 Prerequisites

- Cursor IDE installed
- Kairos MCP Server running
- Python 3.8+ with virtual environment

## ⚙️ Setup Instructions

### Step 1: Configure MCP in Cursor

1. **Open Cursor Settings:**
   - Press `Ctrl+,` (Windows) or `Cmd+,` (Mac)
   - Navigate to "Extensions" → "MCP"

2. **Create MCP Configuration:**
   Create or edit `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "kairos": {
      "description": "🚀 Kairos MCP Server v1.0 - Context as a Service",
      "command": "C:\\Users\\TT\\CLONE\\Kairos_The_Context_Keeper\\venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\TT\\CLONE\\Kairos_The_Context_Keeper\\run_mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:\\Users\\TT\\CLONE\\Kairos_The_Context_Keeper",
        "PYTHONIOENCODING": "utf-8"
      },
      "autoApprove": [
        "kairos.getProjectConstitution",
        "kairos.getSystemHealth",
        "kairos.getContext"
      ],
      "disabled": false
    }
  }
}
```

### Step 2: Verify Connection

1. **Restart Cursor IDE**
2. **Open Cursor Chat** (`Ctrl+L`)
3. **Test Connection:**
   ```
   @kairos.getSystemHealth
   ```

You should see a response with system health metrics.

## 🚀 Usage Examples

### 1. Get Project Standards
```
@kairos.getProjectConstitution({"section": "security"})
```

**Use Case:** Before implementing authentication, get security standards.

### 2. Context-Enhanced Code Development
```
@kairos.getContext({"query": "JWT authentication implementation", "depth": "expert"})
```

**Use Case:** Get comprehensive context including:
- Project security standards
- Related code files
- Best practices
- Historical decisions

### 3. Architecture Guidance
```
@kairos.getContext({"query": "FastAPI microservice architecture patterns", "depth": "detailed"})
```

**Use Case:** Get architecture patterns and principles for new microservices.

## 💡 Advanced Workflows

### Context-Driven Development

1. **Before Writing Code:**
   ```
   @kairos.getContext({"query": "database connection pooling best practices", "depth": "expert"})
   ```

2. **Get Relevant Files:**
   The response will include:
   - Security standards from project constitution
   - Relevant existing code files
   - Best practices
   - Historical context

3. **Write Code with Context:**
   Use the provided context to write code that:
   - Follows project standards
   - Maintains consistency
   - Implements best practices

### Real-Time Project Intelligence

1. **System Health Monitoring:**
   ```
   @kairos.getSystemHealth({"include_metrics": true})
   ```

2. **Architecture Compliance:**
   ```
   @kairos.getProjectConstitution({"section": "architecture"})
   ```

## 🎯 Key Benefits

### 🧠 **Intelligent Context**
- **Multi-source aggregation:** Constitution + Code + History + Best Practices  
- **Confidence scoring:** Know how reliable the context is
- **Caching:** Fast responses for repeated queries

### ⚡ **Enhanced Productivity**
- **200%+ faster development** with context-aware suggestions
- **Consistent code quality** following project standards
- **Reduced context switching** between documentation and code

### 🛡️ **Built-in Compliance**
- **Automatic standard adherence** through project constitution
- **Security best practices** integrated into suggestions
- **Architecture pattern consistency** across codebase

## 🔧 Troubleshooting

### Connection Issues

1. **Check MCP Server Status:**
   ```bash
   echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}' | python src/mcp/kairos_mcp_final.py
   ```

2. **Verify Paths:**
   - Ensure Python path is correct
   - Check virtual environment activation

3. **Review Logs:**
   - Cursor: Help → Developer Tools → Console
   - Kairos: Check terminal output

### Performance Issues

1. **Enable Caching:**
   Context responses are automatically cached for 30 minutes

2. **Adjust Query Depth:**
   - Use `"basic"` for quick responses
   - Use `"expert"` for comprehensive context

## 📈 Success Metrics

After integration, you should see:
- **Faster code development** (2x improvement)
- **Higher code quality** (consistent with project standards)
- **Reduced bugs** (better context awareness)
- **Improved onboarding** (new developers get instant project context)

## 🤝 Community & Support

- **GitHub Issues:** Report problems or request features
- **Documentation:** Check `docs/` folder for more guides
- **Examples:** See `examples/cursor_workflows.md`

---

**🚀 Ready to supercharge your development with Kairos intelligence!**
