"""
OpenAI API provider for ShellMind.

Communicates with OpenAI's API (or any OpenAI-compatible endpoint)
via the chat completions endpoint.
"""

import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

from shellmind.llm.base import BaseLLMProvider, LLMResult
from shellmind.config import LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_TEMPERATURE


# Default model and API URL
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider.

    Works with OpenAI API, Azure OpenAI, and any OpenAI-compatible
    endpoint (like Ollama's OpenAI-compatible mode, LocalAI, etc.).
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = OPENAI_DEFAULT_MODEL,
        api_url: str = OPENAI_API_URL,
    ):
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model
        self.api_url = api_url

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def is_available(self) -> bool:
        """Check if API key is configured."""
        return bool(self._api_key)

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = LLM_TEMPERATURE,
        **kwargs: Any,
    ) -> LLMResult:
        """Send a chat request to the OpenAI API."""
        t0 = time.time()

        if not self._api_key:
            return LLMResult(
                success=False,
                content="OpenAI API key not set. Set OPENAI_API_KEY environment variable or configure it.",
                provider=self.name,
                model=self._model,
                duration=time.time() - t0,
            )

        data = json.dumps({
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            self.api_url,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        for attempt in range(LLM_MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
                    body = json.loads(resp.read())

                content = body.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = body.get("usage", {})
                tokens_in = usage.get("prompt_tokens", 0)
                tokens_out = usage.get("completion_tokens", 0)

                if content:
                    return LLMResult(
                        success=True,
                        content=content,
                        provider=self.name,
                        model=self._model,
                        tokens_in=tokens_in,
                        tokens_out=tokens_out,
                        duration=time.time() - t0,
                    )

            except urllib.error.HTTPError as http_err:
                body = http_err.read().decode()
                try:
                    err_msg = json.loads(body).get("error", {}).get("message", http_err.reason)
                except (json.JSONDecodeError, AttributeError):
                    err_msg = body or http_err.reason

                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(1)
                    continue

                return LLMResult(
                    success=False,
                    content=f"OpenAI HTTP {http_err.code}: {err_msg}",
                    provider=self.name,
                    model=self._model,
                    duration=time.time() - t0,
                )

            except (urllib.error.URLError, OSError) as exc:
                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(1)
                    continue
                return LLMResult(
                    success=False,
                    content=f"OpenAI unreachable: {exc}",
                    provider=self.name,
                    model=self._model,
                    duration=time.time() - t0,
                )

            except Exception as exc:
                return LLMResult(
                    success=False,
                    content=f"OpenAI error: {exc}",
                    provider=self.name,
                    model=self._model,
                    duration=time.time() - t0,
                )

        return LLMResult(
            success=False,
            content="OpenAI returned no content after retries.",
            provider=self.name,
            model=self._model,
            duration=time.time() - t0,
        )
