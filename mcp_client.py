from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

import sys

# 为stdio连接创建服务端参数
server_params = StdioServerParameters(
    command="python",
    args=["./mcp_server.py"],
    env=None,
)

async def run():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            await session.initialize()

            # 列出可用的提示模板
            prompts = await session.list_prompts()
            print("promps: ", prompts)

            # 列出可用资源
            resources = await session.list_resources()
            print("resources: ", resources)

            # 列出可用工具
            tools = await session.list_tools()
            print("tools: ", tools)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run())

