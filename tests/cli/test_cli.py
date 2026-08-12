"""CLI smoke tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from vigil.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_validate_command() -> None:
    result = runner.invoke(
        app, ["policy", "validate", "--policy", "examples/support_agent/vigil.yaml"]
    )
    assert result.exit_code == 0
    assert "policy ok" in result.stdout


def test_from_maul_command(tmp_path: Path) -> None:
    out = tmp_path / "out.yaml"
    result = runner.invoke(
        app,
        [
            "policy",
            "from-maul",
            "examples/support_agent/reliability_report.json",
            "--output",
            str(out),
            "--project",
            "support-agent",
        ],
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "suggestion" in result.stdout


def test_dry_run_command(tmp_path: Path) -> None:
    decisions = tmp_path / "decisions.jsonl"
    audit = tmp_path / "audit.jsonl"
    result = runner.invoke(
        app,
        [
            "policy",
            "dry-run",
            "--policy",
            "examples/support_agent/vigil.yaml",
            "--events",
            "examples/support_agent/events.jsonl",
            "--decisions",
            str(decisions),
            "--audit",
            str(audit),
        ],
    )
    assert result.exit_code == 0
    assert decisions.exists()
    assert "dry-run complete" in result.stdout


def test_validate_invalid_policy(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("version: 1\n", encoding="utf-8")
    result = runner.invoke(app, ["policy", "validate", "--policy", str(bad)])
    assert result.exit_code == 10
