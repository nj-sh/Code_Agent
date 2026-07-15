"""
Base tool classes and data structures for ShellMind's tool system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """Result from executing a single tool call."""

    success: bool
    output: str
    duration: float
    tool: str
    args: dict = field(default_factory=dict)
    cancelled: bool = False


class BaseTool(ABC):
    """Abstract base class for all tools.

    Subclasses must define name, description, and implement execute().
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name (used in tool calls)."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        return ""

    @abstractmethod
    def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""
        ...
