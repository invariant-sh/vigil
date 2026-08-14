# Security Policy

## What Vigil is (and is not)

This repository is the **open-source Vigil SDK**: policy schema, validation, Maul-report conversion, and local dry-run.

It is **not** a public edge proxy, hosted control plane, or production policy gateway. The local Rust gateway and commercial platform are separate. Do not treat `vigil policy dry-run` as live enforcement.

## Credentials and sensitive data

- Keep API keys in the environment or a secret manager. Never commit `.env`, live `vigil.yaml` secrets, or provider credentials.
- Audit events and decision records are redacted by default: hashes, models, counts, and costs only. Do not add prompt bodies or `Authorization` material to artifacts.
- Treat Maul reports, recorded events, and suggestion drafts as potentially sensitive. Prefer scrubbed fixtures in version control.

## Suggestions are not enforcement

`vigil policy from-maul` emits drafts marked `status: suggested`. A human must review scope, limits, and false-positive risk before any deployment. Vigil must not silently convert a test result into a production block.

## Reporting a vulnerability

If you believe you found a security issue in Vigil:

1. **Do not** open a public GitHub issue with exploit details.
2. Contact the maintainers via the [Invariant](https://github.com/invariant-sh) org profile, or open a **private** security advisory on GitHub if enabled.
3. Include: Vigil version/commit, reproduction steps, and impact.

We aim to acknowledge reports within a few business days.

## Safe defaults for operators

- Run the SDK on trusted policies and event files in local or CI environments.
- Do not expose a future Vigil gateway on the open internet without authentication and an approved policy.
- Rotate any key that may have been pasted into a shell history, issue, or commit by mistake.
