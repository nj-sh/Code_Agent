"""
Tool registry for ShellMind's plugin/discovery system.

Tools register themselves with a name, and the agent looks them up
by name when the LLM makes a tool call.
"""

from typing import Any

from shellmind.tools.base import BaseTool, ToolResult


class ToolRegistry:
    """Registry of available tools, keyed by tool name."""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def dispatch(self, name: str, **kwargs: Any) -> ToolResult | None:
        """Execute a tool by name with the given arguments.

        Returns None if the tool is not found.
        """
        tool = self.get(name)
        if tool is None:
            return None
        return tool.execute(**kwargs)

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return sorted(self._tools.keys())

    def get_descriptions(self) -> dict[str, str]:
        """Get descriptions of all registered tools."""
        return {name: tool.description for name, tool in self._tools.items()}
