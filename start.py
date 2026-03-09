import os
import sys
import threading
import time
import webbrowser
import uvicorn
from starlette.middleware.cors import CORSMiddleware
from mcp_app.mcp_server import mcp

def run_server_internal():
    """Starts the MCP server logic directly (merged from run_server.py)."""
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

    port = int(os.environ.get("PORT", 8000))
    print(f"📡 Starting Unified MCP Server (SSE) on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")

def open_browser():
    print("⏳ Waiting for server to initialize...")
    time.sleep(2)  # Give the server a moment to start
    print("🚀 Opening SkyRescue AI simulation in browser...")
    html_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "simulation", "simulation.html"))
    webbrowser.open(f"file://{html_path}")

if __name__ == "__main__":
    if "MISTRAL_API_KEY" not in os.environ:
        print("\n⚠️  WARNING: MISTRAL_API_KEY environment variable is not set.")
        print("   Autonomous LLM coordination will be disabled until a key is provided.\n")
    
    # Start server in a background thread
    server_thread = threading.Thread(target=run_server_internal)
    server_thread.daemon = True
    server_thread.start()

    # Open browser
    open_browser()

    try:
        # Keep main thread alive
        print("\n" + "="*50)
        print("  SkyRescue AI Ecosystem is Active")
        print("  - Server: http://localhost:8000/sse")
        print("  - UI:     simulation/simulation.html")
        print("="*50 + "\n")
        
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down SkyRescue AI...")
        sys.exit(0)
