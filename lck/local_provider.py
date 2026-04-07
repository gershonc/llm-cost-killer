"""Local LLM provider implementations (Ollama-compatible)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Optional
from urllib import error, request


@dataclass
class LocalOllamaProvider:
    """Call a local Ollama server through its HTTP API.

    This provider is compatible with CostOptimizedRouter's `LLMProvider` protocol.
    """

    base_url: str = "http://localhost:11434"
    request_timeout_sec: int = 60

    def generate(self, prompt: str, model: str) -> Dict[str, object]:
        """Generate text from a local model and return router-compatible fields."""
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        req = request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=self.request_timeout_sec) as resp:
                body = resp.read().decode("utf-8")
                data = json.loads(body)
        except error.URLError as exc:
            return {
                "text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error": f"ollama_connection_error: {exc}",
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "text": "",
                "input_tokens": 0,
                "output_tokens": 0,
                "error": f"ollama_request_error: {exc}",
            }

        # Ollama often returns prompt_eval_count/eval_count when stream=False.
        # Fallback to rough token estimates if unavailable.
        in_tokens = int(data.get("prompt_eval_count", max(1, int(len(prompt.split()) * 1.3))))
        out_text = str(data.get("response", "")).strip()
        out_tokens = int(data.get("eval_count", max(1, int(len(out_text.split()) * 1.3))))

        return {
            "text": out_text,
            "input_tokens": in_tokens,
            "output_tokens": out_tokens,
            "error": None,
        }
