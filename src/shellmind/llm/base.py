"""
Base LLM provider interface for ShellMind.

All LLM backends (Ollama, OpenAI, Anthropic, etc.) must implement
this interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResult:
    """Result from an LLM provider call."""
    success: bool
    content: str
    provider: str = ""
    model: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    duration: float = 0.0


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'ollama', 'openai')."""
        ...

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        **kwargs: Any,
    ) -> LLMResult:
        """Send a chat request and return the result."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (server running, API key set, etc.)."""
        ...
