"""Configuration defaults for LLM Cost Killer."""

from dataclasses import dataclass, field
from typing import Dict, Set


@dataclass(frozen=True)
class RoutingSettings:
    """Rule-based routing thresholds for prompt complexity."""

    max_simple_chars: int = 120
    max_simple_words: int = 20
    strong_keywords: Set[str] = field(
        default_factory=lambda: {
            "analyze",
            "compare",
            "reason",
            "code",
            "step by step",
            "architecture",
        }
    )


@dataclass(frozen=True)
class FallbackSettings:
    """Settings used to decide whether cheap output is too weak."""

    min_output_words_for_complex_prompt: int = 24
    enabled: bool = True


DEFAULT_CHEAP_MODEL = "gpt-4.1-mini"
DEFAULT_STRONG_MODEL = "gpt-4.1"

# Prices are USD per 1M tokens.
MODEL_PRICING: Dict[str, Dict[str, float]] = {
    DEFAULT_CHEAP_MODEL: {"input_per_1m": 0.80, "output_per_1m": 3.20},
    DEFAULT_STRONG_MODEL: {"input_per_1m": 5.00, "output_per_1m": 15.00},
}

ROUTING = RoutingSettings()
FALLBACK = FallbackSettings()
