import asyncio
from mcp.client.stdio import stdio_client, StdioServerParameters
from mcp import ClientSession

async def main():
    
    server_params = StdioServerParameters(
        command="python",
        args=["run_server.py"]
    )

    # Launch the MCP server process
    async with stdio_client(server_params) as (read, write):

        async with ClientSession(read, write) as session:

            # Initialize connection
            await session.initialize()

            print("\nConnected to MCP server\n")

            # Discover tools
            response = await session.list_tools()

            print("Available tools:")
            for tool in response.tools:
                print(tool.name)

            # Example tool call
            result = await session.call_tool(
                "list_drones",
                {}
            )

            print("\nDrones detected:")
            print(result)


asyncio.run(main())