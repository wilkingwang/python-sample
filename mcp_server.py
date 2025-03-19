from mcp.server.fastmcp import FastMCP

# 创建一个MCP Server
mcp = FastMCP("Echo")


@mcp.resource("echo://{message}")
def echo_resource(message: str) -> str:
    return f"Resource echo: {message}"


@mcp.tool()
def echo_tool(message: str) -> str:
    return f"Tool echo: {message}"


@mcp.prompt()
def echo_prompt(message: str) -> str:
    return f"Please process this message: {message}"


if __name__ == "__main__":
    mcp.run()