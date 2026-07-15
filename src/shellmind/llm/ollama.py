"""
Ollama LLM provider for ShellMind.

Communicates with a local Ollama server via its REST API.
"""

import json
import time
import urllib.error
import urllib.request

from shellmind.config import OLLAMA_URL, LLM_TIMEOUT, LLM_MAX_RETRIES, LLM_TEMPERATURE
from shellmind.llm.base import BaseLLMProvider, LLMResult


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider — communicates with local Ollama server."""

    def __init__(self, url: str = OLLAMA_URL, model: str = "qwen2.5-coder:3b"):
        self.url = url
        self._model = model

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def model(self) -> str:
        return self._model

    @model.setter
    def model(self, value: str) -> None:
        self._model = value

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            api_base = self.url.replace("/api/chat", "/api/tags")
            req = urllib.request.Request(api_base)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = LLM_TEMPERATURE,
        **kwargs,
    ) -> LLMResult:
        """Send a chat request to Ollama and return the result."""
        t0 = time.time()

        data = json.dumps({
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        }).encode()

        req = urllib.request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        full_content = ""
        tokens_out = 0

        for attempt in range(LLM_MAX_RETRIES):
            try:
                with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as resp:
                    for line in resp:
                        try:
                            chunk = json.loads(line.decode())
                            content = chunk.get("message", {}).get("content", "")
                        except (json.JSONDecodeError, KeyError):
                            continue
                        if content:
                            full_content += content
                            tokens_out += 1

                if full_content:
                    return LLMResult(
                        success=True,
                        content=full_content,
                        provider=self.name,
                        model=self._model,
                        tokens_out=tokens_out,
                        duration=time.time() - t0,
                    )

            except urllib.error.HTTPError as http_err:
                body = http_err.read().decode()
                try:
                    err_body = json.loads(body)
                    err_msg = err_body.get("error", http_err.reason)
                except json.JSONDecodeError:
                    err_msg = body or http_err.reason

                if "not found" in str(err_msg).lower():
                    return LLMResult(
                        success=False,
                        content=f"Model '{self._model}' not found. Pull it: ollama pull {self._model}",
                        provider=self.name,
                        model=self._model,
                        duration=time.time() - t0,
                    )

                if attempt < LLM_MAX_RETRIES - 1:
                    time.sleep(1)
                    continue

                return LLMResult(
                    success=False,
                    content=f"Ollama HTTP {http_err.code}: {err_msg}",
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
                    content=f"Ollama unreachable: {exc}. Is it running? (ollama serve)",
                    provider=self.name,
                    model=self._model,
                    duration=time.time() - t0,
                )

            except Exception as exc:
                return LLMResult(
                    success=False,
                    content=f"Ollama error: {exc}",
                    provider=self.name,
                    model=self._model,
                    duration=time.time() - t0,
                )

        return LLMResult(
            success=False,
            content="Ollama returned no content after retries.",
            provider=self.name,
            model=self._model,
            duration=time.time() - t0,
        )
