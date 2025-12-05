"""CLI entrypoint for Sandboxy."""

import csv
import json
import os
import sys
from pathlib import Path

import click

from sandboxy.agents.loader import AgentLoader
from sandboxy.core.mdl_parser import MDLParseError, apply_variables, load_module, validate_module
from sandboxy.core.runner import Runner

DEFAULT_AGENT_DIRS = [
    Path("agents/core"),
    Path("agents/community"),
    Path.home() / ".sandboxy" / "agents",
]


@click.group()
@click.version_option(package_name="sandboxy")
def main() -> None:
    """Sandboxy CLI - run and validate agent simulations."""
    pass


def _load_variables_from_env() -> dict:
    """Load variables from SANDBOXY_VARIABLES environment variable."""
    env_vars = os.environ.get("SANDBOXY_VARIABLES", "")
    if not env_vars:
        return {}
    try:
        return json.loads(env_vars)
    except json.JSONDecodeError:
        return {}


@main.command()
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--agent-id", "-a", help="Agent ID to use", default=None)
@click.option("--output", "-o", help="Output file for replay JSON", default=None)
@click.option("--pretty", "-p", is_flag=True, help="Pretty print output")
@click.option("--var", "-v", multiple=True, help="Variable in name=value format")
def run(
    module_path: str,
    agent_id: str | None,
    output: str | None,
    pretty: bool,
    var: tuple[str, ...],
) -> None:
    """Run a module with a given agent.

    MODULE_PATH is the path to an MDL YAML file.
    """
    try:
        module = load_module(Path(module_path))
    except MDLParseError as e:
        click.echo(f"Error loading module: {e}", err=True)
        sys.exit(1)

    # Load variables from environment and CLI
    variables = _load_variables_from_env()
    for v in var:
        if "=" in v:
            name, value = v.split("=", 1)
            # Try to parse as JSON for numbers/booleans
            try:
                variables[name] = json.loads(value)
            except json.JSONDecodeError:
                variables[name] = value

    # Apply variables to module
    module = apply_variables(module, variables)

    loader = AgentLoader(DEFAULT_AGENT_DIRS)

    try:
        if agent_id:
            agent = loader.load(agent_id)
        else:
            agent = loader.load_default()
    except ValueError as e:
        click.echo(f"Error loading agent: {e}", err=True)
        sys.exit(1)

    # Apply module's agent_config overrides
    if module.agent_config:
        if "system_prompt" in module.agent_config:
            agent.config.system_prompt = module.agent_config["system_prompt"]

    click.echo(f"Running module: {module.id}")
    click.echo(f"Using agent: {agent.config.id}")
    if variables:
        click.echo(f"Variables: {variables}")
    click.echo("")

    runner = Runner(module=module, agent=agent)
    result = runner.run()

    if output:
        Path(output).write_text(result.to_json(indent=2))
        click.echo(f"Results saved to: {output}")
    elif pretty:
        click.echo(result.pretty())
    else:
        click.echo(result.to_json(indent=2))


@main.command()
@click.argument("module_path", type=click.Path(exists=True))
def validate(module_path: str) -> None:
    """Validate an MDL module.

    MODULE_PATH is the path to an MDL YAML file.
    """
    errors = validate_module(Path(module_path))

    if errors:
        click.echo("Module validation failed:", err=True)
        for error in errors:
            click.echo(f"  - {error}", err=True)
        sys.exit(1)

    click.echo("Module is valid.")


@main.command()
@click.argument("module_path", type=click.Path(exists=True))
@click.option("--agents", required=True, help="Comma-separated agent IDs")
@click.option("--runs-per-agent", type=int, default=1, help="Number of runs per agent")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output CSV file")
@click.option("--var", "-v", multiple=True, help="Variable in name=value format")
@click.option("--seed", type=int, default=None, help="Random seed for reproducibility")
def bench(
    module_path: str,
    agents: str,
    runs_per_agent: int,
    output: str | None,
    var: tuple[str, ...],
    seed: int | None,
) -> None:
    """Benchmark a module against multiple agents.

    MODULE_PATH is the path to an MDL YAML file.

    Examples:
        sandboxy bench modules/lemonade.yml --agents gpt4,claude --runs 5
        sandboxy bench modules/lemonade.yml --agents gpt4 -v difficulty=8 -v starting_cash=100
    """
    import random

    # Set random seed for reproducibility
    if seed is not None:
        random.seed(seed)

    try:
        module = load_module(Path(module_path))
    except MDLParseError as e:
        click.echo(f"Error loading module: {e}", err=True)
        sys.exit(1)

    # Load variables from environment and CLI
    variables = _load_variables_from_env()
    for v in var:
        if "=" in v:
            name, value = v.split("=", 1)
            try:
                variables[name] = json.loads(value)
            except json.JSONDecodeError:
                variables[name] = value

    # Apply variables to module
    if variables:
        module = apply_variables(module, variables)
        click.echo(f"Variables: {variables}")

    loader = AgentLoader(DEFAULT_AGENT_DIRS)
    agent_ids = [a.strip() for a in agents.split(",")]

    results: list[dict[str, str | float | int]] = []

    for agent_id in agent_ids:
        try:
            agent = loader.load(agent_id)
        except ValueError as e:
            click.echo(f"Warning: Skipping agent {agent_id}: {e}", err=True)
            continue

        # Apply module's agent_config overrides
        if module.agent_config:
            if "system_prompt" in module.agent_config:
                agent.config.system_prompt = module.agent_config["system_prompt"]

        click.echo(f"Benchmarking agent: {agent_id}")

        for run_idx in range(runs_per_agent):
            # Generate run-specific seed for reproducibility
            run_seed = seed + run_idx if seed is not None else None

            runner = Runner(module=module, agent=agent)
            result = runner.run()

            row: dict[str, str | float | int] = {
                "agent_id": agent_id,
                "run_idx": run_idx,
                "score": result.evaluation.score,
                "num_events": result.evaluation.num_events,
                "status": result.evaluation.status,
            }

            # Add seed if used
            if run_seed is not None:
                row["seed"] = run_seed

            # Add env_state metrics if available
            if "cash_balance" in runner.env_state:
                row["final_cash"] = runner.env_state["cash_balance"]
            if "starting_cash" in module.environment.initial_state:
                initial = module.environment.initial_state["starting_cash"]
                if "final_cash" in row:
                    row["profit"] = float(row["final_cash"]) - float(initial)

            # Add all evaluation check results
            for check_name, check_result in result.evaluation.checks.items():
                if isinstance(check_result, (int, float, bool)):
                    row[f"check_{check_name}"] = check_result

            results.append(row)
            click.echo(f"  Run {run_idx + 1}: score={result.evaluation.score:.2f}")

    if not results:
        click.echo("No results to report.", err=True)
        sys.exit(1)

    # Output results
    if output:
        fieldnames = list(results[0].keys())
        with open(output, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
        click.echo(f"\nResults saved to: {output}")
    else:
        # Print summary table
        click.echo("\nBenchmark Results:")
        click.echo("-" * 60)

        # Group by agent
        from collections import defaultdict
        by_agent: dict[str, list[dict[str, str | float | int]]] = defaultdict(list)
        for r in results:
            by_agent[str(r["agent_id"])].append(r)

        for agent_id, runs in by_agent.items():
            scores = [r["score"] for r in runs if isinstance(r["score"], (int, float))]
            avg_score = sum(scores) / len(scores) if scores else 0
            click.echo(f"{agent_id}:")
            click.echo(f"  Runs: {len(runs)}")
            click.echo(f"  Avg Score: {avg_score:.3f}")
            if "final_cash" in runs[0]:
                cash_values = [r["final_cash"] for r in runs if "final_cash" in r]
                avg_cash = sum(cash_values) / len(cash_values) if cash_values else 0  # type: ignore
                click.echo(f"  Avg Final Cash: {avg_cash:.2f}")
            click.echo("")


@main.command()
def list_agents() -> None:
    """List available agents."""
    loader = AgentLoader(DEFAULT_AGENT_DIRS)
    agent_ids = loader.list_ids()

    if not agent_ids:
        click.echo("No agents found.")
        click.echo("Agent directories searched:")
        for d in DEFAULT_AGENT_DIRS:
            click.echo(f"  - {d}")
        return

    click.echo("Available agents:")
    for agent_id in sorted(agent_ids):
        config = loader.get_config(agent_id)
        if config:
            click.echo(f"  {agent_id}")
            click.echo(f"    Name: {config.name}")
            click.echo(f"    Model: {config.model}")
            click.echo("")


@main.command()
@click.argument("module_path", type=click.Path(exists=True))
def info(module_path: str) -> None:
    """Show information about a module.

    MODULE_PATH is the path to an MDL YAML file.
    """
    try:
        module = load_module(Path(module_path))
    except MDLParseError as e:
        click.echo(f"Error loading module: {e}", err=True)
        sys.exit(1)

    click.echo(f"Module: {module.id}")
    click.echo(f"Description: {module.description}")
    click.echo("")
    click.echo("Environment:")
    click.echo(f"  Sandbox Type: {module.environment.sandbox_type}")
    click.echo(f"  Tools: {len(module.environment.tools)}")
    for tool in module.environment.tools:
        click.echo(f"    - {tool.name} ({tool.type})")
    click.echo("")
    click.echo(f"Steps: {len(module.steps)}")
    for step in module.steps:
        click.echo(f"  - {step.id}: {step.action}")
    click.echo("")
    click.echo(f"Branches: {len(module.branches)}")
    for name, steps in module.branches.items():
        click.echo(f"  - {name}: {len(steps)} steps")
    click.echo("")
    click.echo(f"Evaluation Checks: {len(module.evaluation)}")
    for check in module.evaluation:
        click.echo(f"  - {check.name} ({check.kind})")


if __name__ == "__main__":
    main()
