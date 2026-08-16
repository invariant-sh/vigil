# Support agent example

Walkthrough for the Vigil SDK open policy foundation.

## Validate a policy

```bash
uv run vigil policy validate --policy examples/support_agent/vigil.yaml
```

## Suggest policy from a Maul report

```bash
uv run vigil policy from-maul examples/support_agent/reliability_report.json \
  --output examples/support_agent/vigil.suggestions.yaml \
  --project support-agent \
  --environment production

# Optional Holds quality gate for model_routing suggestions:
# uv run vigil policy from-maul contracts/maul/reliability_report.v0.2.example.json \
#   --holds-baseline contracts/holds/baseline.v1.example.json \
#   --output vigil.suggestions.yaml
```

The draft is marked `status: suggested`. A human must review before any deployment. Maul schemas `0.1` and `0.2` are accepted.

## Dry-run recorded traffic

```bash
uv run vigil policy dry-run \
  --policy examples/support_agent/vigil.yaml \
  --events examples/support_agent/events.jsonl \
  --decisions artifacts/decisions.jsonl \
  --audit artifacts/audit.jsonl
```

Expected behaviours in the sample events:

| Request | Outcome |
|---|---|
| `req-1` | allow |
| `req-2` | route to `gpt-4o-mini` after cost threshold |
| `req-3`–`req-4` | allow / continue under call cap |
| `req-5` | block (`call_cap_exceeded`) |
| `req-loop-3` | block (`circuit_breaker_tripped`) |
| `req-guard` | block (`tool_content_blocked`) |
| `req-deny-model` | block (`model_not_allowed`) |
