import asyncio
import os
import logging
import json
import sys
from typing import Optional, List, Dict, Any
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from openai import OpenAI

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("document-search-client")

# Disable OpenAI and httpx loggers
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("https").setLevel(logging.WARNING)

# MCP Client
class MCPClient:
    def __init__(self, debug = False):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.debug = debug

        # Message history tracking
        self.message_history = []

        # Main system prompt
        self.system_prompt = "You are a helpful RAG AI assistant named 'RAG-AI-MCP' that can answer questions about the provided documents or query the attached databases for more information."

        # Initialize OpenAI Client
        
        # Server connection info
        self.avaliable_tools = []
        self.avaliable_resources = []
        self.avaliable_prompts = []
        self.server_name = None

    # Connect to MCP Server
    async def connect_to_server(self, server_script_path: str):
        if self.debug:
            logger.info(f"Connecting to server at {server_script_path}")

        is_python = server_script_path.endswith('.py')
        if not (is_python):
            raise ValueError("Server script must be a .py file")
        
        # Initialize server parameters
        server_params = StdioServerParameters(
            command="python",
            args=[server_script_path],
            env=None,
        )

        # Initialize stdio transport
        try:
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            self.stdio, self.write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))

            # Initialize the session
            init_result = await self.session.initialize()
            self.server_name = init_result.serverInfo.name

            if self.debug:
                logger.info(f"Connected to server: {self.server_name} v{init_result.serverInfo.version}")

            # Cache avaliable tools, resources and prompts
            await self.refresh_capabilities()

            return True
        except Exception as e:
            logger.error(f"Failed to connect to server: {e}")
            return False
        
    # Refresh Server Capabilities
    async def refresh_capabilities(self):
        if not self.session:
            raise ValueError(f"Not connected to server")
        
        # Get avaliable tools
        tools_response = await self.session.list_tools()
        self.avaliable_tools = tools_response.tools

        # Get avaliable resources
        resources_response = await self.session.list_resources()
        self.avaliable_resources = resources_response.resources

        # Get avaliable Prompts
        prompts_response = await self.session.list_prompts()
        self.avaliable_prompts = prompts_response.prompts

        if self.debug:
            logger.info(f"Server capabilities refreshed:")
            logger.info(f"- Tools: {len(self.avaliable_tools)}")
            logger.info(f"- Resources: {len(self.avaliable_resources)}")
            logger.info(f"- Prompts: {len(self.avaliable_prompts)}")

    # Handling Message History Helper Function
    async def add_to_history(self, role: str, content: str, metadata: Dict[str, Any] = None):
        message = {
            "role": role,
            "content": content,
            "timestamp": asyncio.get_event_loop().time(),
            "metadata": metadata or {}
        }

        # Add mesage to history
        self.message_history.append(message)

        if self.debug:
            logger.info(f"Added message to history: {role} - {content[:100]}...")

    # List avaliable resources from the mcp server
    async def list_resources(self):
        if not self.session:
            raise ValueError("Not connected to server")
        
        response = await self.session.list_resources()
        self.avaliable_resources = response.resources

        if self.debug:
            resource_uris = [res.uri for res in self.avaliable_resources]
            logger.info(f"Avaliable resources: {resource_uris}")

        return self.avaliable_resources
    
    # Read content from a resource and add to message history
    async def read_resource(self, uri: str):
        if self.debug:
            logger.info(f"Reading resource: {uri}")

        try:
            result = await self.session.read_resource(uri)

            if not result:
                content = "No content found for this resource."
            else:
                content = result if isinstance(result, str) else str(result)

            # Add resource content to hsitory as a user message
            resource_message = f"Resource content from {uri}: \n\n{content}"
            await self.add_to_history("user", resource_message, {"resource_uri": uri, "is_resource": True})

            return content
        except Exception as ex:
            error_msg = f"Error reading resource {uri}: {str(ex)}"
            logger.error(error_msg)
            await self.add_to_history("user", error_msg, {"uri": uri, "error": True})
            return error_msg
        
    # List Avaliable Prompts from the MCP server
    async def list_prompts(self):
        response = await self.session.list_prompts()
        self.avaliable_prompts = response.prompts

        if self.debug:
            prompts_names = [prompt.name for prompt in self.avaliable_prompts]
            logger.info(f"Avaliable prompts: {prompts_names}")

        return self.avaliable_prompts
    
    # Get a specific prompt with arguments
    async def get_prompt(self, name: str, arguments: dict = None):
        if self.debug:
            logger.info(f"Getting prompt: {name} with arguments: {arguments}")

        try:
            prompt_result = await self.session.get_prompt(name, arguments)
            return prompt_result
        except Exception as ex:
            error_msg = f"Error getting prompt {name}: {str(ex)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    # Main chat loop
    async def chat_loop(self):
        print(f"\n{'='*50}")
        print(f"RAG-AI-CMP Client Connected to: {self.server_name}")
        print(f"\n{'='*50}")
        print("Type you queries or use these commands:")
        print("     /debug  - Toggle debug mode")
        print("     /refresh  - Refresh server capabilityes")
        print("     /resources  - List avaliable resources")
        print("     /resource <uri>  - Read a specific resource")
        print("     /prompts  - List avaliable prompts")
        print("     /prompt <name> <argument> - Use a specific prompt with a string as the arguemnt")
        print("     /tools - List avaliable tools")

        # Main chat loop
        while True:
            try:
                query = input("\nQuery: ").strip()

                if query == '/quit':
                    break
                elif query.lower == '/debug':
                    self.debug = not self.debug
                    print(f"\nDebug mode: {'enabled' if self.debug else 'disabled'}")
                    continue
                elif query.lower() == 'refresh':
                    await self.refresh_capabilities()
                    print("\nServer capabilities refreshed")
                    continue
                elif query.lower() == '/resources':
                    resources = await self.list_resources()
                    print("\nAvaliable Resources:")
                    for res in resources:
                        print(f"    - {res.uri}")
                        if res.description:
                            print(f"    {res.description}")
                    continue
                elif query.lower().startswith('/resource'):
                    uri = query[10:].strip()
                    print(f"\nFetching resource: {uri}")
                    content = await self.read_resource(uri)
                    print(f"\nResource Content ({uri}):")
                    print("----------------------------------")
                    if len(content) > 500:
                        print(content[:500] + "...")
                        print("(Resource content truncated for display purpose but full content is included in message history)")
                    else:
                        print(content)
                    
                    continue
                elif query.lower() == '/prompts':
                    prompts = await self.list_prompts()
                    print("\nAvaliable Prompts:")
                    for prompt in prompts:
                        print(f"    - {prompt.name}")
                        if prompt.description:
                            print(f"    {prompt.description}")
                        if prompt.arguments:
                            print(f"    Arguments: {', '.join(arg.name for arg in prompt.arguments)}")

                        continue
                elif query.lower().startswith('/prompt '):
                    parts = query[8:].strip().split(maxsplit=1)
                    if not parts:
                        print("Error: Prompt name required")
                        continue

                    name = parts[0]
                    argument = {}

                    if len(parts) > 1:
                        arg_text = parts[1]

                        prompt_info = None
                        for prompt in self.avaliable_prompts:
                            if prompt.name == name:
                                prompt_info = prompt
                                break
                        
                        if prompt_info and prompt_info.arguments and len(prompt_info.arguments) > 0:
                            argument[prompt_info.arguments[0].name] = arg_text
                        else:
                            argument["text"] = arg_text
                        
                        print(f"\nGetting prompt template: {name} {argument}")
                        prompt_result = await self.get_prompt(name, argument)

                        # TODO
                        messages = prompt_result.messages
                        for msg in messages:
                            content = msg.content.text if hasattr(msg.content, 'text') else str(msg.content)
                            print(content)
                elif query.lower() == '/tools':
                    print("\nAvaliable Tools:")
                    for tool in self.avaliable_tools:
                        print(f"    - {tool.name}")
                        if tool.description:
                            print(f"    {tool.description}")
                
                # TODO

            except Exception as ex:
                print(f"\nError: {str(ex)}")
                if self.debug:
                    import traceback
                    traceback.print_exc()
    
    # Resource cleanup
    async def cleanup(self):
        if self.debug:
            logger.info("Cleaning up client resources")
        
        await self.exit_stack.aclose()
    

# Main Function
async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    # Initialize client
    server_script = sys.argv[1]
    client = MCPClient()

    # Connect to server
    try:
        connected = await client.connect_to_server(server_script)
        if not connected:
            print(f"Failed to connect to server at {server_script}")
            sys.exit(1)

        await client.chat_loop()

    except Exception as ex:
        print(f"Error: {str(ex)}")
        import traceback
        traceback.print_exc()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())