# %%
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List
import asyncio
import nest_asyncio


# %%
nest_asyncio.apply()
load_dotenv()

# %%

#####Query Processing
class MCP_chatbot:
    def __init__(self):
        self.session: ClientSession = None
        self.anthropic = Anthropic()
        self.available_tools: List[dict]    = []
    
    async def process_query(self, query):
        messages = [{'role':'user', 'content':query}]
        response = self.anthropic.messages.create(max_tokens = 2024,
                                  model = 'claude-sonnet-4-20250514',
                                  tools = self.available_tools,
                                  messages = messages)
        process_query = True
        while process_query:
            assistant_content = []
            for content in response.content:
                if content.type =='text':
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content)==1):
                        process_query= False
                elif content.type == 'tool_use':
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name

                    print(f"Calling tool {tool_name} with args {tool_args}")
                    
                    # Call a tool
                    result = await self.session.call_tool(tool_name, arguments=tool_args)
                    messages.append({"role": "user", 
                                    "content": [
                                        {
                                            "type": "tool_result",
                                            "tool_use_id":tool_id,
                                            "content": result.content
                                        }
                                    ]
                                    })
                    response = self.anthropic.messages.create(max_tokens = 2024,
                                    model = 'claude-3-7-sonnet-20250219', 
                                    tools = self.available_tools,
                                    messages = messages) 
                    
                    if(len(response.content)==1 and response.content[0].type == "text"):
                        print(response.content[0].text)
                        process_query= False


# Create Chat Loop
    async def chat_loop(self):
        """ Run an interactive chat loop in the terminal """
        print("\nMCP Research Assistant Started!")
        print("Type your queries or 'quit' to exit.")
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    break
        
                await self.process_query(query)
                print("\n")
            except Exception as e:
                print(f"\nError: {str(e)}")

    #####Building MCP Client
    async def connect_to_mcp_and_run_chatbot(self):
        server_params = StdioServerParameters(
            command="uv",
            args=["run", "research_mcp_server.py"],
            env=None,
        )
        async with stdio_client(server_params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                self.session = session
                await session.initialize( )
                response = await session.list_tools()

                tools = response.tools
                print("/nConnected to MCP server. Available tools:", [tool.name for tool in tools])
                self.available_tools = [{
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema,
                } for tool in response.tools]
                await self.chat_loop()

# %%
async def main():
    chatbot = MCP_chatbot()
    await chatbot.connect_to_mcp_and_run_chatbot()

if __name__ == "__main__":
    asyncio.run(main())