"""TurboQuant-style prompt compression for lower token usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class TurboQuantSettings:
    """Settings for aggressive but safe prompt compression."""

    enabled: bool = True
    min_chars_to_compress: int = 40
    max_words_after_compression: int = 40
    removable_words: Set[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.removable_words is None:
            object.__setattr__(
                self,
                "removable_words",
                {
                    "please",
                    "kindly",
                    "just",
                    "really",
                    "very",
                    "basically",
                    "actually",
                    "maybe",
                    "somewhat",
                    "this",
                    "to",
                    "a",
                    "an",
                    "the",
                },
            )


def _normalize_token(token: str) -> str:
    return "".join(ch for ch in token.lower() if ch.isalnum())


def compress_prompt(prompt: str, settings: TurboQuantSettings) -> Dict[str, object]:
    """Compress prompt text and return compression metadata."""
    original_prompt = prompt.strip()
    if not settings.enabled or len(original_prompt) < settings.min_chars_to_compress:
        return {
            "compressed_prompt": original_prompt,
            "turboquant_used": False,
            "input_tokens_saved_estimate": 0,
        }

    words = original_prompt.split()
    kept_words = []
    for token in words:
        norm = _normalize_token(token)
        if norm and norm in settings.removable_words:
            continue
        kept_words.append(token)

    if len(kept_words) > settings.max_words_after_compression:
        kept_words = kept_words[: settings.max_words_after_compression]

    compressed_prompt = " ".join(kept_words).strip() or original_prompt
    original_token_est = len(words)
    compressed_token_est = len(compressed_prompt.split())
    saved = max(0, original_token_est - compressed_token_est)

    return {
        "compressed_prompt": compressed_prompt,
        "turboquant_used": saved > 0,
        "input_tokens_saved_estimate": saved,
    }
