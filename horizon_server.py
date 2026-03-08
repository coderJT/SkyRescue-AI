"""
Prefect Horizon Entry Point
This file lives at the root to ensure all modules (simulation, drone, agent) 
are correctly discovered by the Python path on cloud platforms.
"""
from mcp_app.mcp_server import mcp

if __name__ == "__main__":
    mcp.run()
