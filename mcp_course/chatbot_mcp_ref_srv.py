# %%
from dotenv import load_dotenv
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
from typing import List, Dict, TypedDict
from contextlib import AsyncExitStack
import json
import asyncio
import nest_asyncio
import logging


# %%
nest_asyncio.apply()
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s [%(name)s] %(message)s',
    datefmt='%m/%d/%y %H:%M:%S'
)
logger = logging.getLogger(__name__)

# %%

class ToolDefinition(TypedDict):
    name: str
    description: str
    input_schema: Dict


# %%

#####Initialize mcp servers and Query Processing
class MCP_chatbot:
    def __init__(self):
        logger.info("Initializing MCP Chatbot")
        self.session: List[ClientSession] = [] # List of MCP client sessions we are connected to
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.available_tools: List[ToolDefinition] = [] # List of tools available to the chatbot
        self.tool_to_session: Dict[str, ClientSession] = {} # Map tool names to their respective MCP sessions
        logger.info("MCP Chatbot initialized successfully")

    async def connect_to_server(self, server_name: str, server_config: dict)-> None:
        """
        Connect to an MCP server and store the session.
        
        Args:
            server_name: Name of the server (for logging purposes)
            server_config: Configuration dictionary for the server connection
        """
        try:
            logger.info(f"Starting connection to {server_name}")
            logger.debug(f"Server config: {server_config}")
            
            server_params = StdioServerParameters(**server_config)
            
            logger.debug(f"Creating stdio transport for {server_name}")
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )

            read, write = stdio_transport

            if server_name == "fetch":
                logger.info(f"Waiting 5.0s for {server_name} to initialize")
                await asyncio.sleep(5.0)
            else:
                logger.debug(f"Waiting 1.0s for {server_name} to initialize")
                await asyncio.sleep(1.0)

            logger.debug(f"Creating session for {server_name}")
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )

            logger.debug(f"Initializing session for {server_name}")
            await session.initialize()
            self.session.append(session)

            #List and store available tools for this session
            logger.debug(f"Listing tools for {server_name}")
            response = await session.list_tools()
            tools = response.tools
            tool_names = [t.name for t in tools]
            
            print(f"\nConnected to {server_name} with tools:", tool_names)
            logger.info(f"Successfully connected to {server_name} with {len(tools)} tools: {tool_names}")

            for tool in tools:
                self.tool_to_session[tool.name] = session
                self.available_tools.append({
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                })
                logger.debug(f"Registered tool '{tool.name}' from {server_name}")
                
        except Exception as e:
            logger.error(f"Failed to connect to {server_name}: {e}", exc_info=True)
            print(f"Failed to connect to {server_name}: {e}")

    async def connect_to_servers(self):
        """ Connect to all MCP servers and store their sessions """
        try:
            logger.info("Loading MCP server configurations")
            with open('mcp_servers_available.json', 'r') as file:
                data = json.load(file)
            servers = data.get("mcpServers", {})
            logger.info(f"Found {len(servers)} servers to connect: {list(servers.keys())}")
            
            for server_name, server_config in servers.items():
                print(f"\n[Connecting to {server_name}...]")
                await self.connect_to_server(server_name, server_config)
            
            logger.info(f"Connection phase complete. Total tools available: {len(self.available_tools)}")
            logger.debug(f"Tool to session mapping: {list(self.tool_to_session.keys())}")
            
        except Exception as e:
            logger.error(f"Error loading server configurations: {e}", exc_info=True)
            print(f"Error loading server configurations: {e}")
            raise

    
    async def process_query(self, query):
        logger.info(f"Processing query: '{query}'")
        messages = [{'role':'user', 'content':query}]
        
        logger.debug(f"Calling Claude API with {len(self.available_tools)} tools")
        response = self.anthropic.messages.create(
            max_tokens = 2024,
            model = 'claude-3-7-sonnet-20250219',
            tools = self.available_tools,
            messages = messages
        )
        
        process_query = True
        iteration = 0
        
        while process_query:
            iteration += 1
            logger.debug(f"Processing iteration {iteration}")
            assistant_content = []
            
            for content in response.content:
                if content.type =='text':
                    logger.debug(f"Received text response: {content.text[:100]}...")
                    print(content.text)
                    assistant_content.append(content)
                    if(len(response.content)==1):
                        logger.info("Query processing complete")
                        process_query= False
                        
                elif content.type == 'tool_use':
                    logger.info(f"Tool use requested: {content.name}")
                    assistant_content.append(content)
                    messages.append({'role':'assistant', 'content':assistant_content})
                    
                    tool_id = content.id
                    tool_args = content.input
                    tool_name = content.name

                    print(f"Calling tool {tool_name} with args {tool_args}")
                    logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
                    
                    try:
                        # Call a tool
                        session = self.tool_to_session.get(tool_name)
                        
                        if session is None:
                            error_msg = f"No session found for tool: {tool_name}"
                            logger.error(error_msg)
                            raise ValueError(error_msg)
                        
                        logger.debug(f"Calling tool {tool_name} on session {id(session)}")
                        result = await session.call_tool(tool_name, arguments=tool_args)
                        logger.info(f"Tool {tool_name} completed successfully")
                        logger.debug(f"Tool result type: {type(result.content)}")

                        tool_result_content = result.content if isinstance(result.content, list) else [{"type": "text", "text": str(result.content)}]
                        
                        messages.append({"role": "user", 
                                        "content": [
                                            {
                                                "type": "tool_result",
                                                "tool_use_id":tool_id,
                                                "content": tool_result_content
                                            }
                                        ]
                                        })
                        
                        logger.debug("Calling Claude API with tool results")
                        response = self.anthropic.messages.create(
                            max_tokens = 2024,
                            model = 'claude-3-7-sonnet-20250219', 
                            tools = self.available_tools,
                            messages = messages
                        ) 
                        
                        if(len(response.content)==1 and response.content[0].type == "text"):
                            logger.debug(f"Final response: {response.content[0].text[:100]}...")
                            print(response.content[0].text)
                            logger.info("Query processing complete after tool use")
                            process_query= False
                            
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}", exc_info=True)
                        print(f"Error executing tool {tool_name}: {e}")
                        raise


# Create Chat Loop
    async def chat_loop(self):
        """ Run an interactive chat loop in the terminal """
        logger.info("Starting chat loop")
        print("\nMCP Research Assistant Started!")
        print("Type your queries or 'quit' to exit.")
        
        query_count = 0
        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() == 'quit':
                    logger.info("User requested quit")
                    break
                
                if not query:
                    logger.debug("Empty query received, skipping")
                    continue
                
                query_count += 1
                logger.info(f"Processing query #{query_count}")
                await self.process_query(query)
                print("\n")
                
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt received")
                break
            except Exception as e:
                logger.error(f"Error in chat loop: {str(e)}", exc_info=True)
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """ Cleanup resources """
        logger.info("Starting cleanup")
        try:
            await self.exit_stack.aclose()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)

# %%
async def main():
    logger.info("=== MCP Chatbot Starting ===")
    chatbot = MCP_chatbot()
    try:
        await chatbot.connect_to_servers()
        await chatbot.chat_loop()
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error in main: {e}", exc_info=True)
    finally:
        await chatbot.cleanup()
        logger.info("=== MCP Chatbot Shutdown Complete ===")

if __name__ == "__main__":
    asyncio.run(main())