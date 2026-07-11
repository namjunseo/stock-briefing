"""MCP server exposing stock-briefing tools (stdio transport).

Lets any MCP client (e.g. Claude Desktop) query the collected
price/news/disclosure data through the same tools the agent uses.

Run directly for testing:
    python mcp_server.py
"""
import os
import sys

# MCP clients launch this script from an arbitrary cwd; anchor to repo root
# so the relative DB path and .env keep working.
_ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)

from mcp.server.fastmcp import FastMCP

from src.agent import tools

mcp = FastMCP("stock-briefing")

mcp.tool()(tools.get_price)
mcp.tool()(tools.search_news)
mcp.tool()(tools.get_disclosures)

if __name__ == "__main__":
    mcp.run()  # stdio transport
