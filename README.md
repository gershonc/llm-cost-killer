# LLM Cost Killer

Cut your LLM costs by 70–90% with smart routing and cost tracking.

LLM Cost Killer is a lightweight Python package that routes requests between a cheap model and a stronger model, applies fallback logic, and tracks estimated token cost per request.

## Features

- Smart rule-based routing (`cheap` for simple prompts, `strong` for complex prompts)
- Automatic fallback to strong model when cheap output is weak or errors
- Per-request cost estimation from model pricing
- JSONL request logging for easy analysis
- Session-level summary (tokens, cost, fallbacks, model mix)
- Offline-ready demo using a built-in mock provider (no API key required)

## Quickstart

```bash
git clone https://github.com/your-username/llm-cost-killer.git
cd llm-cost-killer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python examples/basic_demo.py
```

## Project structure

```text
llm-cost-killer/
├── README.md
├── requirements.txt
├── .env.example
├── examples/
│   └── basic_demo.py
└── lck/
    ├── __init__.py
    ├── config.py
    ├── router.py
    └── cost_tracker.py
```

## Example code

```python
from lck.router import CostOptimizedRouter

router = CostOptimizedRouter()
result = router.run("compare risks in this contract")

print(result["final_model"])
print(result["estimated_cost"])
print(result["fallback_used"])
```

## Sample output

```text
LLM Cost Killer MVP Demo
------------------------------------------------------------
Prompt: classify this support ticket
  optimized -> selected=gpt-4.1-mini final=gpt-4.1-mini fallback=False cost=$0.000051
Prompt: summarize this invoice
  optimized -> selected=gpt-4.1-mini final=gpt-4.1-mini fallback=False cost=$0.000051
Prompt: extract payment terms
  optimized -> selected=gpt-4.1-mini final=gpt-4.1-mini fallback=False cost=$0.000051
Prompt: compare risks in this contract
  optimized -> selected=gpt-4.1 final=gpt-4.1 fallback=False cost=$0.000640
Prompt: write Python code to parse a CSV
  optimized -> selected=gpt-4.1 final=gpt-4.1 fallback=False cost=$0.000645
------------------------------------------------------------
Session summary
  naive strong-only cost: $0.003205
  optimized routed cost:  $0.001439
  estimated savings:      $0.001766 (55.11%)
  fallback count:         0
```

## How it works

1. `CostOptimizedRouter.choose_model(prompt)` applies simple heuristics:
   - Short/simple prompts -> cheap model
   - Prompts with complexity keywords (`analyze`, `compare`, `reason`, `code`, `step by step`, `architecture`) -> strong model
   - Long prompts -> strong model
2. `CostOptimizedRouter.run(prompt)` executes the request and evaluates fallback:
   - Fallback triggers on cheap-model error
   - Fallback triggers on empty output
   - Fallback triggers on too-short output for complex prompts
3. `CostTracker` logs:
   - timestamp
   - prompt preview
   - chosen model
   - input/output tokens
   - estimated cost
   - fallback used

## Plugging in real API calls later

`CostOptimizedRouter` accepts any provider with:

```python
def generate(prompt: str, model: str) -> dict:
    return {
        "text": "...",
        "input_tokens": 123,
        "output_tokens": 456,
        "error": None,  # or "error message"
    }
```

This keeps the MVP simple today while making real OpenAI calls easy to add later.

## Roadmap

- Add real provider integration (OpenAI-first)
- Add SQLite backend for richer querying and dashboards
- Improve routing heuristics with confidence scoring
- Add CLI for batch prompt simulation
- Add tests and benchmark suites
