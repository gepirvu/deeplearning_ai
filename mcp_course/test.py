import asyncio
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from contextlib import AsyncExitStack

async def test():
    exit_stack = AsyncExitStack()
    
    with open('mcp_servers_available.json', 'r') as f:
        data = json.load(f)
    
    servers = data.get("mcpServers", {})
    
    for server_name, server_config in servers.items():
        try:
            print(f"\n[Connecting to {server_name}...]")
            server_params = StdioServerParameters(**server_config)
            
            stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
            read, write = stdio_transport
            session = await exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            response = await session.list_tools()
            print(f"✓ {server_name} connected:", [t.name for t in response.tools])
        except Exception as e:
            print(f"✗ {server_name} failed: {e}")
            import traceback
            traceback.print_exc()
    
    await exit_stack.aclose()

asyncio.run(test())