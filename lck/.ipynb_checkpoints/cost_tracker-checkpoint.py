"""Cost estimation and lightweight JSONL request logging."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List

from lck.config import MODEL_PRICING


def estimate_request_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate request cost in USD from model pricing."""
    pricing = MODEL_PRICING.get(model)
    if not pricing:
        return 0.0
    input_cost = (input_tokens / 1_000_000) * pricing["input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * pricing["output_per_1m"]
    return round(input_cost + output_cost, 8)


@dataclass
class RequestRecord:
    """A normalized request record for storage and reporting."""

    timestamp: str
    prompt_preview: str
    chosen_model: str
    input_tokens: int
    output_tokens: int
    estimated_cost: float
    fallback_used: bool

    def to_dict(self) -> Dict[str, object]:
        return {
            "timestamp": self.timestamp,
            "prompt_preview": self.prompt_preview,
            "chosen_model": self.chosen_model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": self.estimated_cost,
            "fallback_used": self.fallback_used,
        }


class CostTracker:
    """Collects in-memory request stats and appends JSONL logs."""

    def __init__(self, log_path: str = "lck_requests.jsonl") -> None:
        self.log_path = Path(log_path)
        self.records: List[RequestRecord] = []

    def log_request(
        self,
        prompt: str,
        chosen_model: str,
        input_tokens: int,
        output_tokens: int,
        fallback_used: bool,
    ) -> RequestRecord:
        """Create and persist a request record."""
        preview = prompt.strip().replace("\n", " ")[:80]
        record = RequestRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            prompt_preview=preview,
            chosen_model=chosen_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=estimate_request_cost(chosen_model, input_tokens, output_tokens),
            fallback_used=fallback_used,
        )
        self.records.append(record)
        self._append_jsonl(record)
        return record

    def session_summary(self) -> Dict[str, object]:
        """Return aggregate stats for all tracked requests."""
        total_input = sum(r.input_tokens for r in self.records)
        total_output = sum(r.output_tokens for r in self.records)
        total_cost = round(sum(r.estimated_cost for r in self.records), 8)
        fallback_count = sum(1 for r in self.records if r.fallback_used)
        by_model: Dict[str, int] = {}
        for record in self.records:
            by_model[record.chosen_model] = by_model.get(record.chosen_model, 0) + 1
        return {
            "requests": len(self.records),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_estimated_cost": total_cost,
            "fallback_count": fallback_count,
            "requests_by_model": by_model,
        }

    def extend_from(self, records: Iterable[RequestRecord]) -> None:
        """Add existing records to this tracker's session."""
        self.records.extend(records)

    def _append_jsonl(self, record: RequestRecord) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict()) + "\n")
