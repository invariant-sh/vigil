# Vigil

**Production policy gateway for LLM agents.**

Vigil enforces the controls that Maul’s adversarial tests reveal — rate limits, budgets, allow/deny policy, and operational guardrails at the edge.

```text
Agent  →  Maul (chaos)  →  Holds (eval)  →  Vigil (production)
```

> Status: private / early scaffold. Implementation landing next.

## Related

Part of the [Invariant](https://github.com/invariant-sh) tooling family:

| Tool | Role |
|---|---|
| **[Maul](https://github.com/invariant-sh/maul)** | Adversarial proxy — prove resilience under failure |
| **Holds** | Eval harness — did the agent solve the job? |
| **Vigil** (this repo) | Production controls — enforce policy at the edge |

## License

Licensed under the [Apache License, Version 2.0](./LICENSE).
