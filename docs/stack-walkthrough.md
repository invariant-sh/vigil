# Stack walkthrough: Maul → Holds → Vigil

Vigil consumes reviewed Maul evidence and optional Holds quality baselines. Suggestions are never auto-deployed. There is no live gateway in this repository.

## Supported Maul reports

`vigil policy from-maul` accepts Maul `schema_version` `0.1` and `0.2`. Unsupported versions exit with code `21`.

Minimum useful evidence: schema/version, scenario and seed, session/workflow ids when present, budget/cost outcome, and the report path.

## Commands

```bash
# Caps, circuit breakers, and tool guards from Maul alone
uv run vigil policy from-maul \
  contracts/maul/reliability_report.v0.2.example.json \
  --output artifacts/vigil.suggestions.yaml \
  --project support-agent

# model_routing requires a Holds baseline that passed for the fallback model
uv run vigil policy from-maul \
  contracts/maul/reliability_report.v0.2.example.json \
  --output artifacts/vigil.suggestions.yaml \
  --project support-agent \
  --holds-baseline contracts/holds/baseline.v1.example.json

uv run vigil policy validate --policy examples/support_agent/vigil.yaml
uv run vigil policy dry-run \
  --policy examples/support_agent/vigil.yaml \
  --events examples/support_agent/events.jsonl \
  --decisions artifacts/decisions.jsonl \
  --audit artifacts/audit.jsonl
```

The draft is `status: suggested` with no owner. A human reviews scope, limits, and false-positive risk before any future gateway can enforce the same public evaluation vectors used by dry-run.

Holds-side commands and the Maul lifecycle live in the Holds repository (`docs/stack-walkthrough.md`).
