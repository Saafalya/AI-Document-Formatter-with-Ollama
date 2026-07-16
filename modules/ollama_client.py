"""
ollama_client.py
----------------
Local LLM client for Ollama. Used for semantic rule extraction and text rewrites.
Requires Ollama running locally: https://ollama.com
"""

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:11434"
# Optimal for RTX 4060 (8 GB VRAM) + 32 GB RAM — fast, accurate, fits GPU
DEFAULT_MODEL = "llama3.1:8b"


class OllamaClient:
    """Thin wrapper around the Ollama REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 180,
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)).rstrip("/")
        self.model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", timeout))
        self.enabled = os.getenv("OLLAMA_ENABLED", "true").lower() in ("1", "true", "yes")

    def is_available(self) -> bool:
        """Check whether Ollama is reachable."""
        if not self.enabled:
            return False
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Return installed model names."""
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
            return []

    def chat(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> Optional[str]:
        """
        Send a chat completion request to Ollama.

        Returns:
            Model response text, or None on failure.
        """
        if not self.enabled:
            logger.warning("Ollama is disabled (OLLAMA_ENABLED=false).")
            return None

        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        try:
            body = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.base_url}/api/chat",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
            content = data.get("message", {}).get("content", "").strip()
            if content:
                return content
            logger.warning("Ollama returned empty response.")
            return None
        except urllib.error.HTTPError as e:
            logger.error(f"Ollama HTTP error {e.code}: {e.read().decode()[:200]}")
            return None
        except urllib.error.URLError as e:
            logger.error(
                f"Ollama not reachable at {self.base_url}. "
                f"Is Ollama running? Try: ollama pull {self.model}"
            )
            logger.debug(f"URLError: {e}")
            return None
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return None


# Module-level singleton
_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Return shared OllamaClient instance."""
    global _client
    if _client is None:
        _client = OllamaClient()
    return _client
