"""Tests for MCP tool registration behavior in the bridge.

These are regression tests to ensure tools are registered as async wrappers
so the MCP event loop isn't blocked by sync HTTP calls.
"""

import inspect

from binary_ninja_mcp.bridge import binja_mcp_bridge


def test_public_tool_functions_remain_sync_callables():
    assert inspect.iscoroutinefunction(binja_mcp_bridge.list_methods) is False


def test_mcp_registers_async_tool_wrappers():
    tool = binja_mcp_bridge.mcp._tool_manager.get_tool("list_methods")
    assert tool is not None
    assert tool.is_async is True
