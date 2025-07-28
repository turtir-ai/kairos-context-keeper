# Quick Installation Guide

## For Development Testing:
1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Click "..." → "Install from VSIX..."
4. Select the .vsix file after building

## For Local Installation:
```bash
cd mcp-ecosystem-platform/vscode-extension
npm install
npm run compile
vsce package
code --install-extension mcp-ecosystem-platform-1.0.0.vsix
```

## Configuration:
1. Open VS Code Settings (Ctrl+,)
2. Search for "MCP Platform"
3. Set API URL: http://localhost:8000
4. Optionally set API Key
5. Check status bar for MCP indicator

## Testing:
- Use Ctrl+Shift+P → "MCP Platform" commands
- Right-click files → MCP Platform options
- Check status bar for server status
