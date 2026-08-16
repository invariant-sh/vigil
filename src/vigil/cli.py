"""Vigil CLI entrypoint."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from vigil import __version__
from vigil.adapters.audit.jsonl_sink import JsonlAuditSink, JsonlDecisionSink
from vigil.adapters.config.loader import YamlPolicyLoader
from vigil.adapters.events.jsonl import JsonlEventSource
from vigil.adapters.holds.baseline_reader import JsonHoldsBaselineReader
from vigil.adapters.maul.report_reader import JsonMaulReportReader
from vigil.adapters.runtime import SystemClock, UuidFactory
from vigil.adapters.suggestions_writer import YamlSuggestionWriter
from vigil.application.dry_run import DryRunService
from vigil.application.exit_codes import ExitCode
from vigil.application.from_maul import FromMaulService
from vigil.application.validate import ValidatePolicyService
from vigil.domain.errors import (
    AuditError,
    DryRunError,
    EventSourceError,
    HoldsBaselineError,
    MaulReportError,
    PolicyValidationError,
    UnsupportedReportVersionError,
    VigilError,
)

app = typer.Typer(
    name="vigil",
    help="Runtime policy foundation and AI FinOps helpers for LLM agents.",
    no_args_is_help=True,
    add_completion=False,
)

policy_app = typer.Typer(
    name="policy",
    help="Author, validate, and dry-run Vigil policies.",
    no_args_is_help=True,
)
app.add_typer(policy_app, name="policy")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(__version__)
        raise typer.Exit(code=ExitCode.SUCCESS)


@app.callback()
def main(
    version: Annotated[
        bool | None,
        typer.Option("--version", help="Show version and exit.", callback=_version_callback),
    ] = None,
) -> None:
    """Vigil command group."""
    del version


@policy_app.command("validate")
def validate_command(
    policy: Annotated[Path, typer.Option("--policy", help="Path to vigil.yaml")] = Path(
        "vigil.yaml"
    ),
) -> None:
    """Validate a policy document and print its content hash."""
    service = ValidatePolicyService(policy_loader=YamlPolicyLoader())
    try:
        result = service.execute(policy)
    except PolicyValidationError as error:
        typer.secho(f"invalid policy: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INVALID_POLICY) from error
    except VigilError as error:
        typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INTERNAL) from error

    typer.echo(
        f"policy ok: version={result.policy.version} "
        f"project={result.policy.scope.project} "
        f"environment={result.policy.scope.environment} "
        f"hash={result.policy.content_hash}"
    )


@policy_app.command("from-maul")
def from_maul_command(
    report: Annotated[Path, typer.Argument(help="Path to Maul reliability_report.json")],
    output: Annotated[
        Path, typer.Option("--output", help="Destination for suggestion draft YAML")
    ] = Path("vigil.suggestions.yaml"),
    project: Annotated[
        str, typer.Option("--project", help="Project name for the draft scope")
    ] = "unnamed-project",
    environment: Annotated[
        str, typer.Option("--environment", help="Environment for the draft scope")
    ] = "production",
    holds_baseline: Annotated[
        Path | None,
        typer.Option(
            "--holds-baseline",
            help="Optional Holds baseline proving fallback-model quality for routing suggestions",
        ),
    ] = None,
) -> None:
    """Convert a Maul report into human-reviewable policy suggestions."""
    quality = None
    if holds_baseline is not None:
        try:
            quality = JsonHoldsBaselineReader().read(holds_baseline)
        except HoldsBaselineError as error:
            typer.secho(f"invalid Holds baseline: {error}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=ExitCode.INVALID_HOLDS_BASELINE) from error
    service = FromMaulService(
        report_reader=JsonMaulReportReader(),
        suggestion_writer=YamlSuggestionWriter(),
    )
    try:
        result = service.execute(
            report,
            output_path=output,
            project=project,
            environment=environment,
            holds_quality=quality,
        )
    except UnsupportedReportVersionError as error:
        typer.secho(f"unsupported report: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.UNSUPPORTED_REPORT_VERSION) from error
    except MaulReportError as error:
        typer.secho(f"invalid Maul report: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INVALID_MAUL_REPORT) from error
    except VigilError as error:
        typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INTERNAL) from error

    typer.echo(
        f"wrote {len(result.draft.suggestions)} suggestion(s) "
        f"(status={result.draft.status}) to {result.output_path}"
    )


@policy_app.command("dry-run")
def dry_run_command(
    policy: Annotated[Path, typer.Option("--policy", help="Path to vigil.yaml")] = Path(
        "vigil.yaml"
    ),
    events: Annotated[
        Path, typer.Option("--events", help="Path to recorded request events JSONL")
    ] = Path("events.jsonl"),
    decisions: Annotated[
        Path, typer.Option("--decisions", help="Destination for decision records JSONL")
    ] = Path("artifacts/decisions.jsonl"),
    audit: Annotated[
        Path | None,
        typer.Option("--audit", help="Optional audit.jsonl destination"),
    ] = None,
) -> None:
    """Replay recorded events against a policy and emit decision records."""
    service = DryRunService(
        policy_loader=YamlPolicyLoader(),
        event_source=JsonlEventSource(),
        decision_sink=JsonlDecisionSink(),
        audit_sink=JsonlAuditSink(),
        clock=SystemClock(),
        ids=UuidFactory(),
    )
    try:
        result = service.execute(
            policy_path=policy,
            events_path=events,
            decisions_path=decisions,
            audit_path=audit,
        )
    except PolicyValidationError as error:
        typer.secho(f"invalid policy: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INVALID_POLICY) from error
    except EventSourceError as error:
        typer.secho(f"events error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.EVENT_SOURCE_FAILURE) from error
    except DryRunError as error:
        typer.secho(f"dry-run error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.DRY_RUN_FAILURE) from error
    except AuditError as error:
        typer.secho(f"audit error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.AUDIT_FAILURE) from error
    except VigilError as error:
        typer.secho(f"error: {error}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=ExitCode.INTERNAL) from error

    typer.echo(
        f"dry-run complete: allow={result.allowed_count} "
        f"block={result.blocked_count} route={result.routed_count} "
        f"decisions={result.decisions_path}"
    )
    if result.audit_path is not None:
        typer.echo(f"audit={result.audit_path}")
