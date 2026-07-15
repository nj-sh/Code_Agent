"""
Animated dots spinner for ShellMind's LLM wait states.
"""

import sys
import threading
import time
from typing import Optional

from shellmind.ui.colors import C


class Spinner:
    """Animated dots spinner for LLM wait states."""

    def __init__(self, text: str = "Thinking"):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._text = text
        self._frames = ["●○○○", "○●○○", "○○●○", "○○○●"]

    def start(self) -> None:
        """Start the spinner animation in a background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        """Animate the spinner frames."""
        i = 0
        while self._running:
            sys.stdout.write(f"\r{C.ACCENT}{self._frames[i]} {self._text}{C.RESET}")
            sys.stdout.flush()
            i = (i + 1) % len(self._frames)
            time.sleep(0.15)

    def stop(self) -> None:
        """Stop the spinner and clear the line."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=0.5)
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()
