"""Basic demo comparing naive strong usage vs routed usage."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List

# Allows running: python examples/basic_demo.py
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lck.cost_tracker import CostTracker, estimate_request_cost
from lck.local_provider import LocalOllamaProvider
from lck.router import CostOptimizedRouter, MockLLMProvider


PROMPTS: List[str] = [
    "classify this support ticket",
    "summarize this invoice",
    "extract payment terms",
    "compare risks in this contract",
    "write Python code to parse a CSV",
]


def run_demo() -> None:
    use_local_ollama = os.getenv("LCK_USE_LOCAL_OLLAMA", "false").lower() == "true"
    if use_local_ollama:
        base_url = os.getenv("LCK_OLLAMA_BASE_URL", "http://localhost:11434")
        provider = LocalOllamaProvider(base_url=base_url)
        print(f"Provider: LocalOllamaProvider ({base_url})")
    else:
        provider = MockLLMProvider()
        print("Provider: MockLLMProvider (offline demo)")

    router_tracker = CostTracker(log_path="logs/optimized_requests.jsonl")
    router = CostOptimizedRouter(provider=provider, tracker=router_tracker)

    naive_total = 0.0
    optimized_total = 0.0

    print("LLM Cost Killer MVP Demo")
    print("-" * 60)

    for prompt in PROMPTS:
        naive_result = provider.generate(prompt=prompt, model=router.strong_model)
        naive_cost = estimate_request_cost(
            router.strong_model,
            int(naive_result["input_tokens"]),
            int(naive_result["output_tokens"]),
        )
        naive_total += naive_cost

        optimized_result = router.run(prompt)
        optimized_total += float(optimized_result["estimated_cost"])

        print(f"Prompt: {prompt}")
        print(
            "  optimized -> selected={selected} final={final} fallback={fallback} "
            "turboquant={turboquant} saved_in_tokens~{saved} cost=${cost:.6f}".format(
                selected=optimized_result["selected_model"],
                final=optimized_result["final_model"],
                fallback=optimized_result["fallback_used"],
                turboquant=optimized_result["turboquant_used"],
                saved=optimized_result["input_tokens_saved_estimate"],
                cost=optimized_result["estimated_cost"],
            )
        )

    savings = max(0.0, naive_total - optimized_total)
    savings_pct = (savings / naive_total * 100.0) if naive_total else 0.0

    print("-" * 60)
    print("Session summary")
    print(f"  naive strong-only cost: ${naive_total:.6f}")
    print(f"  optimized routed cost:  ${optimized_total:.6f}")
    print(f"  estimated savings:      ${savings:.6f} ({savings_pct:.2f}%)")
    print(f"  fallback count:         {router_tracker.session_summary()['fallback_count']}")
    print(f"  turboquant count:       {router_tracker.session_summary()['turboquant_count']}")


if __name__ == "__main__":
    run_demo()
