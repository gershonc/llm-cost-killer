"""Routing and fallback logic for LLM Cost Killer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Protocol

from lck.config import (
    DEFAULT_CHEAP_MODEL,
    DEFAULT_STRONG_MODEL,
    FALLBACK,
    ROUTING,
    TURBOQUANT,
)
from lck.cost_tracker import CostTracker
from lck.turboquant import TurboQuantSettings, compress_prompt


class LLMProvider(Protocol):
    """Minimal provider interface to keep model calls swappable."""

    def generate(self, prompt: str, model: str) -> Dict[str, object]:
        """
        Run a generation request.

        Returns a dict with:
        - text: str
        - input_tokens: int
        - output_tokens: int
        - error: Optional[str]
        """


@dataclass
class MockLLMProvider:
    """Deterministic provider so demos run without API access."""

    cheap_model: str = DEFAULT_CHEAP_MODEL
    strong_model: str = DEFAULT_STRONG_MODEL

    def generate(self, prompt: str, model: str) -> Dict[str, object]:
        prompt_lower = prompt.lower()
        input_tokens = max(8, int(len(prompt.split()) * 1.3))

        if model == self.cheap_model:
            if any(k in prompt_lower for k in ("compare", "code", "architecture")):
                return {
                    "text": "",
                    "input_tokens": input_tokens,
                    "output_tokens": 0,
                    "error": "cheap_model_quality_error",
                }
            if any(k in prompt_lower for k in ("analyze", "reason", "step by step")):
                return {
                    "text": "Needs deeper analysis.",
                    "input_tokens": input_tokens,
                    "output_tokens": 4,
                    "error": None,
                }
            text = (
                "Quick result: categorized ticket, extracted key fields, and drafted "
                "a concise summary."
            )
            return {
                "text": text,
                "input_tokens": input_tokens,
                "output_tokens": max(12, int(len(text.split()) * 1.2)),
                "error": None,
            }

        text = (
            "Detailed result: provided a structured answer with reasoning, risks, "
            "trade-offs, and implementation-ready next steps."
        )
        return {
            "text": text,
            "input_tokens": input_tokens,
            "output_tokens": max(40, int(len(text.split()) * 1.8)),
            "error": None,
        }


class CostOptimizedRouter:
    """Routes requests to cheap/strong models and applies fallback rules."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        cheap_model: str = DEFAULT_CHEAP_MODEL,
        strong_model: str = DEFAULT_STRONG_MODEL,
        tracker: Optional[CostTracker] = None,
        turboquant_settings: Optional[TurboQuantSettings] = None,
    ) -> None:
        self.provider = provider or MockLLMProvider(cheap_model=cheap_model, strong_model=strong_model)
        self.cheap_model = cheap_model
        self.strong_model = strong_model
        self.tracker = tracker or CostTracker()
        self.turboquant_settings = turboquant_settings or TurboQuantSettings(
            enabled=TURBOQUANT.enabled,
            min_chars_to_compress=TURBOQUANT.min_chars_to_compress,
            max_words_after_compression=TURBOQUANT.max_words_after_compression,
        )

    def choose_model(self, prompt: str) -> str:
        """Choose cheap or strong model from simple complexity heuristics."""
        prompt_lower = prompt.lower().strip()
        word_count = len(prompt_lower.split())
        char_count = len(prompt_lower)
        has_complex_keyword = any(keyword in prompt_lower for keyword in ROUTING.strong_keywords)

        if has_complex_keyword:
            return self.strong_model
        if char_count > ROUTING.max_simple_chars or word_count > ROUTING.max_simple_words:
            return self.strong_model
        return self.cheap_model

    def run(self, prompt: str) -> Dict[str, object]:
        """Run a request with routing + fallback and log request cost."""
        selected_model = self.choose_model(prompt)
        request_prompt = prompt
        turboquant_used = False
        saved_input_tokens_estimate = 0
        if selected_model == self.cheap_model:
            compression = compress_prompt(prompt, settings=self.turboquant_settings)
            request_prompt = str(compression["compressed_prompt"])
            turboquant_used = bool(compression["turboquant_used"])
            saved_input_tokens_estimate = int(compression["input_tokens_saved_estimate"])

        result = self.provider.generate(prompt=request_prompt, model=selected_model)

        fallback_used = False
        final_model = selected_model

        if selected_model == self.cheap_model and FALLBACK.enabled:
            if self._should_fallback(prompt, result):
                fallback_used = True
                final_model = self.strong_model
                result = self.provider.generate(prompt=prompt, model=self.strong_model)

        record = self.tracker.log_request(
            prompt=prompt,
            chosen_model=final_model,
            input_tokens=int(result.get("input_tokens", 0)),
            output_tokens=int(result.get("output_tokens", 0)),
            fallback_used=fallback_used,
            turboquant_used=turboquant_used,
            input_tokens_saved_estimate=saved_input_tokens_estimate,
        )
        return {
            "prompt": prompt,
            "request_prompt": request_prompt,
            "selected_model": selected_model,
            "final_model": final_model,
            "response": str(result.get("text", "")),
            "error": result.get("error"),
            "fallback_used": fallback_used,
            "turboquant_used": turboquant_used,
            "input_tokens_saved_estimate": saved_input_tokens_estimate,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "estimated_cost": record.estimated_cost,
        }

    def _is_complex_prompt(self, prompt: str) -> bool:
        prompt_lower = prompt.lower()
        if any(k in prompt_lower for k in ROUTING.strong_keywords):
            return True
        return len(prompt_lower) > ROUTING.max_simple_chars

    def _should_fallback(self, prompt: str, result: Dict[str, object]) -> bool:
        error = result.get("error")
        text = str(result.get("text", "")).strip()

        if error:
            return True
        if not text:
            return True

        if self._is_complex_prompt(prompt):
            output_words = len(text.split())
            if output_words < FALLBACK.min_output_words_for_complex_prompt:
                return True

        return False
