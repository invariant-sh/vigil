# Vigil

**Runtime governance and AI FinOps helpers for LLM agents.**

Vigil is the production control member of the Invariant stack. This repository is the **open-source SDK**: policy schema, validation, Maul-report-to-policy conversion, explainable dry-run, and correlation helpers.

```text
Agent  →  Maul (chaos)  →  Holds (eval)  →  Vigil (production)
```

The commercial Vigil Platform (org budgets, dashboards, hosted policy distribution) is separate. The local Rust gateway is a later milestone; this SDK defines the policy semantics that gateway will enforce.

## Install

```bash
uv sync --extra dev
uv run vigil --version
```

## Quick start

```bash
# Validate a policy
uv run vigil policy validate --policy contracts/policy.v1.example.yaml

# Convert a Maul reliability report into reviewable suggestions
uv run vigil policy from-maul path/to/reliability_report.json \
  --output vigil.suggestions.yaml

# Dry-run recorded events against a policy
uv run vigil policy dry-run \
  --policy vigil.yaml \
  --events events.jsonl \
  --decisions artifacts/decisions.jsonl \
  --audit artifacts/audit.jsonl
```

See [`examples/support_agent/`](./examples/support_agent/) for a full walkthrough.

## Policy schema (v1)

```yaml
version: 1
scope:
  project: support-agent
  environment: production
budgets:
  max_llm_calls_per_workflow: 12
  max_cost_usd_per_workflow: 0.75
models:
  allow: [gpt-4o-mini, gpt-4.1-mini]
  route_after_cost_usd: 0.40
  fallback_model: gpt-4o-mini
controls:
  - type: circuit_breaker
    condition: repeated_equivalent_request
    max_occurrences: 3
  - type: tool_content_guard
    mode: block
    patterns: [instruction_override]
audit:
  emit: true
```

Suggestions from Maul are never auto-deployed. Lifecycle is explicit: `suggested` → `approved` → `deployed` (or `rejected`).

## Architecture

Hexagonal layout (mirrors Holds):

```text
cli → application services → domain (pure evaluation)
                ↓
              ports ← adapters (YAML, Maul JSON, JSONL)
```

- Frozen slotted dataclasses, no Pydantic
- Integer micro-USD for money (matches Maul reports)
- Redacted audit events (no prompts, no Authorization)

## Correlation

```python
from vigil.correlation import CorrelationContext, merge_openai_client_kwargs

kwargs = merge_openai_client_kwargs(
    CorrelationContext(
        project="support-agent",
        environment="production",
        workflow_id="wf-123",
    ),
    base_url="http://localhost:8080/v1",
)
```

Without correlation metadata Vigil can enforce per-request limits but cannot claim precise per-workflow spend or loop detection.

## Development

```bash
uv run ruff format .
uv run ruff check .
uv run ty check
uv run pytest --cov=vigil --cov-report=term-missing
uv run python scripts/check_crap.py
```

## Related

| Tool | Role |
|---|---|
| **[Maul](https://github.com/invariant-sh/maul)** | Adversarial proxy — find failure modes |
| **[Holds](https://github.com/invariant-sh/holds)** | Eval harness — measure task quality |
| **Vigil** (this repo) | Policy foundation — enforce approved limits |

## License

Licensed under the [Apache License, Version 2.0](./LICENSE).
