"""
MCP Server Entry Point — SSE Transport
Runs the MCP server over HTTP with SSE so browsers can connect directly.
"""
import os
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from mcp_app.mcp_server import mcp

# Set Mistral API key from environment if available
# (already handled in mcp_server.py, but ensure it's propagated)

# Get the Starlette SSE app from FastMCP
app = mcp.sse_app()

# Add CORS middleware so browsers can access the MCP server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting MCP Server (SSE transport) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)