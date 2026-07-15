"""
LLM provider registry for ShellMind.

Auto-detects available providers (Ollama, OpenAI, Anthropic) and
allows warm switching between them at runtime via the :provider command.
"""

import os
from typing import Optional

from shellmind.llm.base import BaseLLMProvider, LLMResult
from shellmind.llm.ollama import OllamaProvider
from shellmind.llm.openai import OpenAIProvider


class ProviderRegistry:
    """Registry of LLM providers with auto-detection and switching."""

    def __init__(self):
        self._providers: dict[str, BaseLLMProvider] = {}
        self._active: Optional[str] = None
        self._auto_detect()

    def _auto_detect(self) -> None:
        """Detect and register all available providers."""
        # Always try Ollama
        ollama = OllamaProvider()
        self.register(ollama)
        if ollama.is_available():
            self._active = ollama.name

        # Try OpenAI if API key is set
        openai = OpenAIProvider()
        self.register(openai)
        if openai.is_available() and self._active is None:
            self._active = openai.name

        # Fallback to Ollama even if not reachable
        if self._active is None:
            self._active = "ollama"

    def register(self, provider: BaseLLMProvider) -> None:
        """Register a provider."""
        self._providers[provider.name] = provider

    @property
    def active_provider(self) -> BaseLLMProvider:
        """Get the currently active provider."""
        name = self._active or "ollama"
        return self._providers.get(name, self._providers.get("ollama", OllamaProvider()))

    @active_provider.setter
    def active_provider(self, name: str) -> None:
        """Switch to a different provider by name."""
        if name in self._providers:
            self._active = name
        else:
            raise ValueError(f"Unknown provider: {name}. Available: {', '.join(self.list_providers())}")

    def get(self, name: str) -> Optional[BaseLLMProvider]:
        """Get a specific provider by name."""
        return self._providers.get(name)

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return sorted(self._providers.keys())

    def list_available(self) -> list[str]:
        """List only providers that are currently available."""
        return sorted(
            name for name, prov in self._providers.items()
            if prov.is_available()
        )

    def chat(self, messages: list[dict], temperature: float = 0.1) -> LLMResult:
        """Send a chat request to the active provider."""
        provider = self.active_provider
        return provider.chat(messages, temperature=temperature)

    @property
    def active_name(self) -> str:
        return self._active or "ollama"

    @property
    def active_model(self) -> str:
        return self.active_provider.model

    @active_model.setter
    def active_model(self, value: str) -> None:
        self.active_provider.model = value

    def __repr__(self) -> str:
        available = ", ".join(self.list_available())
        return f"ProviderRegistry(active={self._active}, available=[{available}])"
