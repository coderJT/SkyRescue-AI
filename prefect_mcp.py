from prefect import flow
import uvicorn
import os
from run_server import app

@flow(name="SkyRescue MCP Server")
def skyrescue_mcp_flow():
    """
    Prefect Flow that orchestrates and runs the SkyRescue AI MCP server.
    """
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting SkyRescue MCP Server via Prefect on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    # Run the flow directly
    skyrescue_mcp_flow()
