"""Click-based CLI for cyber_range operations: validate, plan, provision (dry-run by default)."""
import json
from pathlib import Path
import click

from src.validator.scenario_validator import ScenarioValidator
from src.planner.planner import plan_scenario
from src.provisioner.provisioner import provision, default_executor
from src.reporter.utils import load_session_from_jsonl, aggregate_events
from src.reporter.pdf_reporter import generate_pdf_from_events


@click.group()
def cli():
    """Cyber Range Deployer CLI"""
    pass


@cli.command()
@click.argument("scenario_file", type=click.Path(exists=True))
def validate(scenario_file: str):
    """Validate a scenario JSON file."""
    data = json.loads(Path(scenario_file).read_text())
    validator = ScenarioValidator()
    result = validator.validate(data)
    if result.is_valid:
        click.echo("VALID: Scenario passed validation")
        if result.has_warnings:
            click.echo("Warnings:")
            for w in result.warnings:
                click.echo(f"  - {w}")
    else:
        click.echo("INVALID: Errors found")
        for e in result.errors:
            click.echo(f"  - {e}")
        raise SystemExit(1)


@cli.command()
@click.argument("scenario_file", type=click.Path(exists=True))
def plan(scenario_file: str):
    """Plan deployment order and resources for a scenario."""
    data = json.loads(Path(scenario_file).read_text())
    plan_result = plan_scenario(data)
    if not plan_result.is_successful:
        click.echo("Planning errors:")
        for e in plan_result.errors:
            click.echo(f"  - {e}")
        raise SystemExit(1)
    click.echo("Deployment order:")
    for i, hid in enumerate(plan_result.ordered_components, start=1):
        click.echo(f"  {i}. {hid}")
    if plan_result.warnings:
        click.echo("Warnings:")
        for w in plan_result.warnings:
            click.echo(f"  - {w}")


@cli.command(name="provision-cmd")
@click.argument("scenario_file", type=click.Path(exists=True))
@click.option("--execute", is_flag=True, default=False, help="Execute Docker commands (not just dry-run)")
@click.option("--isolate", is_flag=True, default=False, help="Apply security isolation options to containers")
@click.option("--parallel", is_flag=True, default=False, help="Enable parallel provisioning for independent hosts")
def provision_cmd(scenario_file: str, execute: bool, isolate: bool, parallel: bool):
    """Provision scenario (dry-run by default)."""
    data = json.loads(Path(scenario_file).read_text())
    plan_result = plan_scenario(data)
    if not plan_result.is_successful:
        click.echo("Planning errors:")
        for e in plan_result.errors:
            click.echo(f"  - {e}")
        raise SystemExit(1)
    # Preflight: verify Docker daemon is reachable when executing
    if execute:
        code = 0
        try:
            code, out, err = default_executor(["docker", "info"])
        except Exception as ex:
            click.echo(f"Failed to invoke docker: {ex}")
            raise SystemExit(1)
        if code != 0:
            click.echo("Docker does not appear to be running or accessible.")
            click.echo(
                "- Start Docker Desktop (macOS) and wait until it says "
                "'Docker is running'."
            )
            click.echo(
                "- Or ensure your DOCKER_HOST/context points to a running "
                "daemon (e.g., colima start)."
            )
            click.echo("- You can re-run without --execute for a safe dry-run.")
            raise SystemExit(1)
    prov_result = provision(
        plan_result,
        data,
        dry_run=not execute,
        executor=default_executor if execute else None,
        isolate=isolate,
        parallel=parallel,
    )
    click.echo("Operations:")
    for op in prov_result.operations:
        click.echo(f"- {op['type']}: {' '.join(op['cmd'])}")
    if prov_result.errors:
        click.echo("Errors:")
        for e in prov_result.errors:
            click.echo(f"  - {e}")
        if execute:
            raise SystemExit(1)


@cli.command()
@click.argument("session_log", type=click.Path(exists=True))
@click.argument("output_pdf", type=click.Path())
def report(session_log: str, output_pdf: str):
    """Generate a PDF report from a session JSONL log."""
    session_id, events = load_session_from_jsonl(session_log)
    # Optionally aggregate for console preview
    agg = aggregate_events(events)
    click.echo(f"Session: {session_id}")
    click.echo("Event type counts:")
    for k, v in sorted(agg.get("counts", {}).items()):
        click.echo(f"  - {k}: {v}")
    generate_pdf_from_events(output_pdf, session_id, events)
    click.echo(f"PDF report written to {output_pdf}")


@cli.command(name="provision")
@click.argument("scenario_file", type=click.Path(exists=True))
@click.option("--execute", is_flag=True, default=False, help="Execute Docker commands (not just dry-run)")
@click.option("--isolate", is_flag=True, default=False, help="Apply security isolation options to containers")
def provision_short(scenario_file: str, execute: bool, isolate: bool):
    """Alias: same as provision-cmd."""
    provision_cmd.callback(
        scenario_file=scenario_file,
        execute=execute,
        isolate=isolate,
        parallel=False
    )  # type: ignore


if __name__ == "__main__":
    cli()
