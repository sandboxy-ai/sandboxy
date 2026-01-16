"""CLI entrypoint for Sandboxy."""

import json
import os
import sys
from pathlib import Path
from typing import Any

import click
from dotenv import load_dotenv

# Load .env file from current directory and parents
load_dotenv()  # Loads .env from cwd
load_dotenv(Path.home() / ".sandboxy" / ".env")  # Also check ~/.sandboxy/.env

from sandboxy.agents.loader import AgentLoader
from sandboxy.core.mdl_parser import MDLParseError, apply_variables, load_module, validate_module
from sandboxy.core.runner import Runner
from sandboxy.scenarios.loader import load_scenario
from sandboxy.scenarios.runner import ScenarioRunner
from sandboxy.tools.loader import get_yaml_tool_libraries

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


@main.command()
@click.argument("shell", type=click.Choice(["bash", "zsh", "fish"]), default="bash")
def completion(shell: str) -> None:
    """Generate shell completion and show setup instructions.

    Writes completion script to ~/.sandboxy-completion.<shell>
    and shows the line to add to your shell config.

    Examples:
        sandboxy completion         # Generate bash completion
        sandboxy completion zsh     # Generate zsh completion
    """
    import subprocess

    home = Path.home()
    ext = shell if shell != "bash" else "bash"
    completion_file = home / f".sandboxy-completion.{ext}"

    # Generate completion script using Click's built-in mechanism
    env = os.environ.copy()
    env["_SANDBOXY_COMPLETE"] = f"{shell}_source"

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "sandboxy.cli.main"],
        env=env,
        capture_output=True,
        text=True,
    )

    # Write to file
    completion_file.write_text(result.stdout)
    click.echo(f"Generated: {completion_file}")
    click.echo("")
    click.echo("Add this line to your shell config:")
    click.echo("")

    if shell == "bash":
        click.echo("# Sandboxy completion")
        click.echo(f'. "{completion_file}"')
        click.echo("")
        click.echo("(Add to ~/.bashrc)")
    elif shell == "zsh":
        click.echo("# Sandboxy completion")
        click.echo(f'. "{completion_file}"')
        click.echo("")
        click.echo("(Add to ~/.zshrc)")
    elif shell == "fish":
        click.echo("# Sandboxy completion")
        click.echo(f'source "{completion_file}"')
        click.echo("")
        click.echo("(Add to ~/.config/fish/config.fish)")


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
@click.option("--with-examples", is_flag=True, help="Include example scenarios and tools")
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(path_type=Path),
    default=None,
    help="Directory to initialize (default: current directory)",
)
def init(with_examples: bool, directory: Path | None) -> None:
    """Initialize a new Sandboxy project.

    Creates the standard folder structure for scenarios, tools, agents, and datasets.

    Examples:
        sandboxy init
        sandboxy init --with-examples
        sandboxy init --dir my-project
    """
    root = directory or Path.cwd()

    # Create directory if specified and doesn't exist
    if directory and not root.exists():
        root.mkdir(parents=True)
        click.echo(f"Created directory: {root}")

    # Standard folders
    folders = ["scenarios", "tools", "agents", "datasets", "runs"]
    created = []

    for folder in folders:
        folder_path = root / folder
        if not folder_path.exists():
            folder_path.mkdir(parents=True)
            created.append(folder)

    if created:
        click.echo(f"Created folders: {', '.join(created)}")
    else:
        click.echo("All folders already exist")

    # Create .env.example if it doesn't exist
    env_example = root / ".env.example"
    if not env_example.exists():
        env_example.write_text(
            """# Sandboxy Environment Variables
# Copy this to .env and fill in your API keys

# OpenRouter API key (recommended - access to 400+ models)
OPENROUTER_API_KEY=

# Or use direct provider keys
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
"""
        )
        click.echo("Created .env.example")

    # Create .gitignore if it doesn't exist
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            """.env
runs/
__pycache__/
*.pyc
"""
        )
        click.echo("Created .gitignore")

    # Add examples if requested
    if with_examples:
        _create_example_files(root)

    click.echo("")
    click.echo("Project initialized! Next steps:")
    click.echo("  1. Copy .env.example to .env and add your API key")
    click.echo("  2. Create scenarios in scenarios/")
    click.echo("  3. Run: sandboxy open")


def _create_example_files(root: Path) -> None:
    """Create example scenario and tool files."""
    # Example scenario
    example_scenario = root / "scenarios" / "hello-world.yml"
    if not example_scenario.exists():
        example_scenario.write_text(
            """name: Hello World
description: A simple greeting scenario to test your setup

system_prompt: |
  You are a friendly assistant. Greet the user warmly.

prompt: |
  Hello! Can you introduce yourself?

evaluation:
  goals:
    - id: greeted
      name: Greeted the user
      description: The assistant should greet the user
      outcome: true
      check: "'hello' in response.lower() or 'hi' in response.lower()"
"""
        )
        click.echo("Created scenarios/hello-world.yml")

    # Example tool
    example_tool = root / "tools" / "calculator.yml"
    if not example_tool.exists():
        example_tool.write_text(
            """name: calculator
description: A simple calculator tool

tools:
  calculator:
    description: Perform basic math operations
    actions:
      add:
        description: Add two numbers
        parameters:
          type: object
          properties:
            a:
              type: number
              description: First number
            b:
              type: number
              description: Second number
          required: [a, b]
        returns:
          result: "{{a}} + {{b}}"

      multiply:
        description: Multiply two numbers
        parameters:
          type: object
          properties:
            a:
              type: number
            b:
              type: number
          required: [a, b]
        returns:
          result: "{{a}} * {{b}}"
"""
        )
        click.echo("Created tools/calculator.yml")

    # Example scenario using the tool
    tool_scenario = root / "scenarios" / "calculator-test.yml"
    if not tool_scenario.exists():
        tool_scenario.write_text(
            """name: Calculator Test
description: Test the calculator tool

system_prompt: |
  You are a helpful assistant with access to a calculator.
  Use the calculator tool to perform math operations.

tools_from:
  - calculator

prompt: |
  What is 42 + 17?

evaluation:
  goals:
    - id: used_calculator
      name: Used calculator
      description: The agent should use the calculator tool
      outcome: true
      check: "any(tc.tool == 'calculator' for tc in tool_calls)"

    - id: correct_answer
      name: Correct answer
      description: The response should contain 59
      outcome: true
      check: "'59' in response"
"""
        )
        click.echo("Created scenarios/calculator-test.yml")


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
@click.option("--port", "-p", type=int, default=8000, help="Port to run server on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--no-browser", is_flag=True, help="Don't open browser automatically")
def open(port: int, host: str, no_browser: bool) -> None:
    """Open the local Sandboxy UI.

    Starts the API server and opens the web interface in your browser.
    Loads scenarios, tools, and agents from the current working directory.

    Examples:
        sandboxy open
        sandboxy open --port 3000
        sandboxy open --no-browser
    """
    import threading
    import time
    import webbrowser

    import uvicorn

    from sandboxy.api.app import create_local_app

    root_dir = Path.cwd()
    local_ui_path = Path(__file__).parent.parent / "ui" / "dist"

    app = create_local_app(
        root_dir,
        local_ui_path if local_ui_path.exists() else None,
    )

    url = f"http://{host}:{port}"
    click.echo(f"Starting Sandboxy at {url}")
    click.echo(f"Working directory: {root_dir}")
    click.echo("")

    if not no_browser:

        def open_browser() -> None:
            time.sleep(1.5)
            webbrowser.open(url)

        threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


@main.command()
@click.option("--port", "-p", type=int, default=8000, help="Port to run server on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option(
    "--dir",
    "-d",
    "directory",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=None,
    help="Working directory (default: current directory)",
)
def serve(port: int, host: str, directory: Path | None) -> None:
    """Serve the Sandboxy API (backend only, no UI).

    Useful for running the API server while developing the frontend separately,
    or for headless/API-only deployments.

    Examples:
        sandboxy serve
        sandboxy serve --port 3001
        sandboxy serve --dir /path/to/project
        sandboxy serve --host 0.0.0.0  # Allow external connections
    """
    import uvicorn

    from sandboxy.api.app import create_local_app

    root_dir = directory or Path.cwd()

    # No UI - backend API only
    app = create_local_app(root_dir, local_ui_path=None)

    url = f"http://{host}:{port}"
    click.echo(f"Starting Sandboxy API at {url}")
    click.echo(f"Working directory: {root_dir}")
    click.echo("")
    click.echo("API endpoints:")
    click.echo(f"  {url}/api/local/status")
    click.echo(f"  {url}/api/local/scenarios")
    click.echo(f"  {url}/api/local/tools")
    click.echo(f"  {url}/docs  (OpenAPI docs)")
    click.echo("")

    uvicorn.run(app, host=host, port=port, log_level="info")


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


@main.command()
@click.argument("scenario_path", type=click.Path(exists=True))
@click.option(
    "--model",
    "-m",
    help="Model to use (e.g., openai/gpt-4o, anthropic/claude-3.5-sonnet)",
    default=None,
)
@click.option("--agent-id", "-a", help="Agent ID from config files", default=None)
@click.option("--output", "-o", help="Output file for results JSON", default=None)
@click.option("--pretty", "-p", is_flag=True, help="Pretty print output")
@click.option("--max-turns", type=int, default=20, help="Maximum conversation turns")
@click.option("--var", "-v", multiple=True, help="Variable in name=value format")
def scenario(
    scenario_path: str,
    model: str | None,
    agent_id: str | None,
    output: str | None,
    pretty: bool,
    max_turns: int,
    var: tuple[str, ...],
) -> None:
    """Run a scenario with YAML-defined tools.

    SCENARIO_PATH is the path to a scenario YAML file.

    Scenarios support YAML-defined tools that don't require Python code.
    Tools can be defined inline or loaded from tool libraries.

    Examples:
        sandboxy scenario scenarios/trolley.yml -m openai/gpt-4o
        sandboxy scenario scenarios/trolley.yml -m anthropic/claude-3.5-sonnet -p
        sandboxy scenario scenarios/surgeon.yml -v patient="John Smith" -v condition="critical"
    """
    from sandboxy.agents.base import AgentConfig
    from sandboxy.agents.llm_prompt import LlmPromptAgent
    from sandboxy.scenarios.loader import apply_scenario_variables

    try:
        spec = load_scenario(Path(scenario_path))
    except ValueError as e:
        click.echo(f"Error loading scenario: {e}", err=True)
        sys.exit(1)

    # Parse and apply variables
    variables: dict[str, Any] = {}
    for v in var:
        if "=" in v:
            name, value = v.split("=", 1)
            # Try to parse as JSON for numbers/booleans
            try:
                variables[name] = json.loads(value)
            except json.JSONDecodeError:
                variables[name] = value

    if variables:
        spec = apply_scenario_variables(spec, variables)
        click.echo(f"Variables: {variables}")

    # Determine which agent to use
    agent = None

    if model:
        # Create ad-hoc agent from model string
        config = AgentConfig(
            id=model,
            name=model.split("/")[-1] if "/" in model else model,
            kind="llm-prompt",
            model=model,
            system_prompt="",
            tools=[],
            params={"temperature": 0.7, "max_tokens": 4096},
            impl={},
        )
        agent = LlmPromptAgent(config)
    elif agent_id:
        # Load from agent config files
        loader = AgentLoader(DEFAULT_AGENT_DIRS)
        try:
            agent = loader.load(agent_id)
        except ValueError as e:
            click.echo(f"Error loading agent: {e}", err=True)
            sys.exit(1)
    else:
        # Try to load default, but give helpful message if none available
        loader = AgentLoader(DEFAULT_AGENT_DIRS)
        try:
            agent = loader.load_default()
        except ValueError:
            click.echo("No model specified. Use -m to specify a model:", err=True)
            click.echo("", err=True)
            click.echo("  sandboxy scenario <file> -m openai/gpt-4o", err=True)
            click.echo("  sandboxy scenario <file> -m anthropic/claude-3.5-sonnet", err=True)
            click.echo("  sandboxy scenario <file> -m google/gemini-2.0-flash-exp:free", err=True)
            click.echo("", err=True)
            click.echo(
                "Or set OPENROUTER_API_KEY and use any model from openrouter.ai/models", err=True
            )
            sys.exit(1)

    # Apply scenario's system prompt to agent
    if spec.system_prompt:
        agent.config.system_prompt = spec.system_prompt

    click.echo(f"Running scenario: {spec.name}")
    click.echo(f"Using model: {agent.config.model}")
    click.echo(f"Tools loaded: {len(spec.tools) + len(spec.tools_from)} source(s)")
    click.echo("")

    runner = ScenarioRunner(scenario=spec, agent=agent)
    result = runner.run(max_turns=max_turns)

    if output:
        Path(output).write_text(result.to_json(indent=2))
        click.echo(f"\nResults saved to: {output}")
    elif pretty:
        click.echo(result.pretty())
    else:
        click.echo(result.to_json(indent=2))


@main.command()
def list_tools() -> None:
    """List available YAML tool libraries."""
    libraries = get_yaml_tool_libraries()

    if not libraries:
        click.echo("No YAML tool libraries found.")
        click.echo("Tool directories searched:")
        click.echo("  - tools/")
        return

    click.echo("Available YAML tool libraries:")
    for lib in sorted(libraries):
        click.echo(f"  - {lib}")

    click.echo("")
    click.echo("Use in scenarios with:")
    click.echo("  tools_from:")
    click.echo("    - <library_name>")


# Common models for quick reference (Updated January 2026)
POPULAR_MODELS = [
    # Free models
    ("google/gemini-2.0-flash-exp:free", "Free", "Gemini 2.0 Flash - fast & free"),
    ("deepseek/deepseek-r1:free", "Free", "DeepSeek R1 - reasoning model"),
    ("meta-llama/llama-3.3-70b-instruct:free", "Free", "Llama 3.3 70B"),
    ("qwen/qwen-2.5-72b-instruct:free", "Free", "Qwen 2.5 72B"),
    # Budget models (< $0.50/M input)
    ("openai/gpt-4o-mini", "$0.15/M", "GPT-4o Mini"),
    ("openai/gpt-4.1-nano", "$0.10/M", "GPT-4.1 Nano"),
    ("openai/gpt-5-mini", "$0.30/M", "GPT-5 Mini - newest budget"),
    ("google/gemini-2.0-flash", "$0.10/M", "Gemini 2.0 Flash"),
    ("google/gemini-3-flash", "$0.30/M", "Gemini 3 Flash - newest"),
    ("x-ai/grok-4-fast", "$0.20/M", "Grok 4 Fast - 2M context"),
    ("deepseek/deepseek-chat", "$0.30/M", "DeepSeek V3"),
    ("anthropic/claude-3-haiku", "$0.25/M", "Claude 3 Haiku"),
    # Mid-tier models ($0.50 - $2.00/M input)
    ("anthropic/claude-haiku-4.5", "$1.00/M", "Claude Haiku 4.5 - newest fast"),
    ("openai/o3-mini", "$1.10/M", "o3 Mini - reasoning"),
    ("google/gemini-2.5-pro", "$1.25/M", "Gemini 2.5 Pro"),
    ("openai/gpt-5.1", "$1.25/M", "GPT-5.1"),
    ("openai/gpt-5.2", "$1.75/M", "GPT-5.2 - newest"),
    ("deepseek/deepseek-r1", "$0.70/M", "DeepSeek R1 - reasoning"),
    # Premium models ($2.00 - $5.00/M input)
    ("google/gemini-3-pro", "$2.00/M", "Gemini 3 Pro - newest"),
    ("openai/gpt-4.1", "$2.00/M", "GPT-4.1 - 1M context"),
    ("anthropic/claude-sonnet-4.5", "$3.00/M", "Claude Sonnet 4.5 - newest"),
    ("anthropic/claude-3.5-sonnet", "$3.00/M", "Claude 3.5 Sonnet"),
    ("x-ai/grok-4", "$3.00/M", "Grok 4 - 2M context"),
    ("openai/o1-mini", "$3.00/M", "o1 Mini - reasoning"),
    ("anthropic/claude-opus-4.5", "$5.00/M", "Claude Opus 4.5 - newest best"),
    # Frontier models (> $5.00/M input)
    ("openai/o1", "$15.00/M", "o1 - advanced reasoning"),
    ("openai/o3", "$20.00/M", "o3 - newest reasoning"),
    ("openai/gpt-5.2-pro", "$21.00/M", "GPT-5.2 Pro - maximum capability"),
    ("openai/o1-pro", "$150.00/M", "o1 Pro - extended thinking"),
]


@main.command()
@click.option("--fetch", "-f", is_flag=True, help="Fetch full list from OpenRouter API")
@click.option("--free", is_flag=True, help="Show only free models")
@click.option("--search", "-s", help="Search for models by name")
def list_models(fetch: bool, free: bool, search: str | None) -> None:
    """List available models from OpenRouter.

    By default shows popular models. Use --fetch to get the full list.

    Examples:
        sandboxy list-models
        sandboxy list-models --free
        sandboxy list-models --fetch --search claude
    """
    if fetch:
        # Fetch from OpenRouter API
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            click.echo("OPENROUTER_API_KEY not set. Showing popular models instead.", err=True)
            click.echo("")
            fetch = False

    if fetch:
        _fetch_and_display_models(free, search)
    else:
        _display_popular_models(free, search)


def _display_popular_models(free_only: bool, search: str | None) -> None:
    """Display curated list of popular models."""
    click.echo("Popular Models (via OpenRouter):")
    click.echo("")

    for model_id, price, desc in POPULAR_MODELS:
        if free_only and price != "Free":
            continue
        if search and search.lower() not in model_id.lower() and search.lower() not in desc.lower():
            continue

        click.echo(f"  {model_id}")
        click.echo(f"    {desc} [{price}]")
        click.echo("")

    click.echo("Usage:")
    click.echo("  sandboxy scenario <file> -m openai/gpt-4o-mini")
    click.echo("")
    click.echo("Set your API key:")
    click.echo("  export OPENROUTER_API_KEY=sk-or-...")
    click.echo("")
    click.echo("Browse all models: https://openrouter.ai/models")
    click.echo("Use --fetch to query the full list from OpenRouter API")


def _fetch_and_display_models(free_only: bool, search: str | None) -> None:
    """Fetch and display models from OpenRouter API."""
    try:
        import httpx
    except ImportError:
        click.echo("httpx package required. Install with: pip install httpx", err=True)
        return

    api_key = os.getenv("OPENROUTER_API_KEY", "")

    try:
        with httpx.Client() as client:
            resp = client.get(
                "https://openrouter.ai/api/v1/models",
                headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        click.echo(f"Error fetching models: {e}", err=True)
        click.echo("Falling back to popular models list.", err=True)
        click.echo("")
        _display_popular_models(free_only, search)
        return

    models = data.get("data", [])

    # Filter and sort
    filtered = []
    for m in models:
        model_id = m.get("id", "")
        name = m.get("name", model_id)
        pricing = m.get("pricing", {})
        prompt_price = float(pricing.get("prompt", 0)) * 1_000_000  # Per million tokens

        is_free = prompt_price == 0

        if free_only and not is_free:
            continue

        if search:
            search_lower = search.lower()
            if search_lower not in model_id.lower() and search_lower not in name.lower():
                continue

        filtered.append(
            {
                "id": model_id,
                "name": name,
                "price": "Free" if is_free else f"${prompt_price:.2f}/M",
                "context": m.get("context_length", 0),
            }
        )

    # Sort by price (free first, then by cost)
    filtered.sort(
        key=lambda x: (
            0 if x["price"] == "Free" else float(x["price"].replace("$", "").replace("/M", ""))
        )
    )

    click.echo(f"Models from OpenRouter ({len(filtered)} found):")
    click.echo("")

    for m in filtered[:50]:  # Limit output
        click.echo(f"  {m['id']}")
        ctx = f"{m['context'] // 1000}k" if m["context"] >= 1000 else str(m["context"])
        click.echo(f"    {m['name']} [{m['price']}] [ctx: {ctx}]")

    if len(filtered) > 50:
        click.echo(f"  ... and {len(filtered) - 50} more")

    click.echo("")
    click.echo("Usage: sandboxy scenario <file> -m <model-id>")


# -----------------------------------------------------------------------------
# Scaffolding Commands
# -----------------------------------------------------------------------------

SCENARIO_TEMPLATE = """# {title}
# {description}

id: {id}
name: "{title}"
description: |
  {description}

category: general
tags:
  - example

# Import tools from libraries (optional)
# tools_from:
#   - my_tool_library

# Define inline tools
tools:
  check_status:
    description: "Check the current status"
    params:
      target:
        type: string
        required: true
        description: "What to check"
    returns: "Status of {{target}}: OK"

  perform_action:
    description: "Perform an action"
    params:
      action:
        type: string
        required: true
      confirm:
        type: boolean
        required: false
        default: false
    error_when: "confirm != true and confirm != True"
    returns_error: "Action requires confirmation. Set confirm=true."
    returns: "Action '{{action}}' completed successfully."
    side_effects:
      - set: "last_action"
        value: "{{action}}"
      - set: "action_confirmed"
        value: true

# Initial state for the scenario
initial_state:
  status: "nominal"
  alert_level: 0

# System prompt for the AI agent
system_prompt: |
  You are an AI assistant in this scenario.

  Use the available tools to:
  1. Assess the situation
  2. Take appropriate action
  3. Explain your reasoning

# Conversation flow
steps:
  - id: initial_prompt
    action: inject_user
    params:
      content: |
        Welcome to the scenario. What would you like to do?

  - id: agent_response
    action: await_agent

  # Add more steps as needed:
  # - id: followup
  #   action: inject_user
  #   params:
  #     content: "What's your next move?"
  #
  # - id: agent_followup
  #   action: await_agent

# Goals for scoring
goals:
  - id: checked_status
    name: "Checked Status"
    description: "Used check_status tool"
    points: 10
    detection:
      type: tool_called
      tool: check_status

  - id: took_action
    name: "Took Action"
    description: "Performed an action with confirmation"
    points: 20
    detection:
      type: env_state
      key: action_confirmed
      value: true

# Scoring configuration
scoring:
  max_score: 30
  # Optional formula: "checked_status + took_action"
"""

TOOL_LIBRARY_TEMPLATE = """# {title}
# {description}

name: {name}
description: |
  {description}

tools:
  # Example: Simple tool with static return
  get_info:
    description: "Get information about something"
    params:
      item:
        type: string
        required: true
        description: "The item to get info about"
    returns: "Info for {{item}}: This is example data."

  # Example: Tool with state modification
  update_setting:
    description: "Update a setting value"
    params:
      key:
        type: string
        required: true
      value:
        type: string
        required: true
    returns: "Setting '{{key}}' updated to '{{value}}'."
    side_effects:
      - set: "setting_{{key}}"
        value: "{{value}}"

  # Example: Tool with confirmation requirement
  dangerous_action:
    description: "Perform a dangerous action (requires confirmation)"
    params:
      target:
        type: string
        required: true
      confirm:
        type: boolean
        required: true
        description: "Must be true to proceed"
    error_when: "confirm != true and confirm != True"
    returns_error: "This action requires confirmation. Set confirm=true to proceed."
    returns: "Dangerous action performed on {{target}}."
    side_effects:
      - set: "{{target}}_modified"
        value: true

  # Example: Tool with conditional returns
  check_status:
    description: "Check status of a system"
    params:
      system:
        type: string
        required: true
    returns:
      - when: "{{system}}_modified == true"
        value: "System {{system}}: MODIFIED - Changes pending"
      - when: "{{system}}_offline == true"
        value: "System {{system}}: OFFLINE"
      - when: "default"
        value: "System {{system}}: ONLINE - All systems nominal"

  # Example: Tool with enum constraint
  set_mode:
    description: "Set the operating mode"
    params:
      mode:
        type: string
        required: true
        enum: ["normal", "maintenance", "emergency"]
        description: "Operating mode"
    returns: "Mode set to: {{mode}}"
    side_effects:
      - set: "current_mode"
        value: "{{mode}}"
"""


@main.group()
def new() -> None:
    """Create new scenarios and tool libraries."""
    pass


@new.command("scenario")
@click.argument("name")
@click.option("--title", "-t", help="Human-readable title", default=None)
@click.option("--description", "-d", help="Brief description", default="A new scenario")
@click.option("--output-dir", "-o", help="Output directory", default="scenarios")
def new_scenario(name: str, title: str | None, description: str, output_dir: str) -> None:
    """Create a new scenario stub.

    NAME is the scenario identifier (e.g., 'my-scenario' or 'trolley_problem').

    Examples:
        sandboxy new scenario my-test
        sandboxy new scenario data-center-fire -t "Data Center Fire" -d "Handle a fire emergency"
    """
    # Normalize name
    scenario_id = name.lower().replace(" ", "-").replace("_", "-")
    filename = f"{scenario_id.replace('-', '_')}.yml"

    # Generate title if not provided
    if title is None:
        title = " ".join(word.capitalize() for word in scenario_id.split("-"))

    # Create output directory if needed
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / filename

    if file_path.exists():
        click.echo(f"Error: {file_path} already exists", err=True)
        sys.exit(1)

    # Generate content
    content = SCENARIO_TEMPLATE.format(
        id=scenario_id,
        title=title,
        description=description,
    )

    file_path.write_text(content)
    click.echo(f"Created scenario: {file_path}")
    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1. Edit {file_path} to customize your scenario")
    click.echo(f"  2. Run: sandboxy scenario {file_path} -p")


@new.command("tool")
@click.argument("name")
@click.option("--title", "-t", help="Human-readable title", default=None)
@click.option("--description", "-d", help="Brief description", default="A collection of mock tools")
@click.option("--output-dir", "-o", help="Output directory", default="tools")
def new_tool(name: str, title: str | None, description: str, output_dir: str) -> None:
    """Create a new tool library stub.

    NAME is the library name (e.g., 'mock_hospital' or 'space-station').

    Examples:
        sandboxy new tool mock_hospital
        sandboxy new tool space-station -t "Space Station Tools" -d "Tools for space station scenarios"
    """
    # Normalize name - tool libraries use underscores by convention
    lib_name = name.lower().replace("-", "_").replace(" ", "_")

    # Ensure it starts with mock_ for clarity
    if not lib_name.startswith("mock_"):
        lib_name = f"mock_{lib_name}"

    filename = f"{lib_name}.yml"

    # Generate title if not provided
    if title is None:
        title = " ".join(word.capitalize() for word in lib_name.replace("mock_", "").split("_"))
        title = f"Mock {title} Tools"

    # Create output directory if needed
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / filename

    if file_path.exists():
        click.echo(f"Error: {file_path} already exists", err=True)
        sys.exit(1)

    # Generate content
    content = TOOL_LIBRARY_TEMPLATE.format(
        name=lib_name,
        title=title,
        description=description,
    )

    file_path.write_text(content)
    click.echo(f"Created tool library: {file_path}")
    click.echo("")
    click.echo("Next steps:")
    click.echo(f"  1. Edit {file_path} to add your tools")
    click.echo("  2. Use in scenarios with:")
    click.echo("     tools_from:")
    click.echo(f"       - {lib_name}")


# -----------------------------------------------------------------------------
# MCP Commands
# -----------------------------------------------------------------------------


@main.group()
def mcp() -> None:
    """MCP (Model Context Protocol) tools."""
    pass


@mcp.command("inspect")
@click.argument("target", required=False)
@click.option("--url", "-u", help="URL of remote MCP server (HTTP transport)")
@click.option("--args", "-a", "cmd_args", multiple=True, help="Arguments for local server command")
@click.option(
    "--header", "-H", "headers", multiple=True, help="HTTP headers (key:value) for remote servers"
)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["auto", "sse", "streamable_http"]),
    default="auto",
    help="HTTP transport type (default: auto-detect)",
)
def mcp_inspect(
    target: str | None,
    url: str | None,
    cmd_args: tuple[str, ...],
    headers: tuple[str, ...],
    transport: str,
) -> None:
    """Inspect an MCP server and list its available tools.

    For LOCAL servers (stdio), provide the command:
        sandboxy mcp inspect "npx -y @modelcontextprotocol/server-filesystem /tmp"

    For REMOTE servers (HTTP), use --url:
        sandboxy mcp inspect --url "https://example.com/mcp"
        sandboxy mcp inspect --url "https://example.com/sse" --transport sse
        sandboxy mcp inspect --url "https://api.example.com/mcp" -H "Authorization:Bearer token"
    """
    import asyncio
    import shlex

    if not target and not url:
        click.echo(
            "Error: Provide either a command (for local servers) or --url (for remote servers)",
            err=True,
        )
        sys.exit(1)

    # Parse headers into dict
    headers_dict: dict[str, str] = {}
    for h in headers:
        if ":" in h:
            key, value = h.split(":", 1)
            headers_dict[key.strip()] = value.strip()

    async def _inspect_local(command: str, args: list[str]) -> list[dict[str, Any]]:
        from sandboxy.mcp.client import inspect_mcp_server

        return await inspect_mcp_server(command, args)

    async def _inspect_remote(url: str) -> list[dict[str, Any]]:
        from sandboxy.mcp.client import inspect_mcp_server_http

        return await inspect_mcp_server_http(url, headers_dict if headers_dict else None, transport)  # type: ignore[arg-type]

    async def _inspect() -> None:
        try:
            if url:
                # Remote server
                click.echo(f"Connecting to remote MCP server: {url}")
                if headers_dict:
                    click.echo(f"  Headers: {list(headers_dict.keys())}")
                click.echo(f"  Transport: {transport}")
                click.echo("")
                tools = await _inspect_remote(url)
            else:
                # Local server
                command = target or ""
                args = list(cmd_args)

                # Parse command if it's a single string with spaces
                if not args and " " in command:
                    parts = shlex.split(command)
                    command = parts[0]
                    args = parts[1:]

                click.echo(f"Connecting to local MCP server: {command} {' '.join(args)}")
                click.echo("")
                tools = await _inspect_local(command, args)

            if not tools:
                click.echo("No tools found.")
                return

            click.echo(f"Found {len(tools)} tool(s):")
            click.echo("")

            for tool in tools:
                click.echo(f"  {tool['name']}")
                if tool.get("description"):
                    click.echo(f"    {tool['description']}")

                params = tool.get("parameters", [])
                if params:
                    click.echo("    Parameters:")
                    for p in params:
                        req = " (required)" if p.get("required") else ""
                        desc = f" - {p.get('description')}" if p.get("description") else ""
                        click.echo(f"      - {p['name']}: {p.get('type', 'any')}{req}{desc}")

                click.echo("")

            # Show usage example
            click.echo("Use in scenarios with:")
            click.echo("  mcp_servers:")
            click.echo("    - name: my_server")
            if url:
                click.echo(f"      url: {url}")
                if headers_dict:
                    click.echo("      headers:")
                    for k, v in headers_dict.items():
                        click.echo(f"        {k}: {v}")
                if transport != "auto":
                    click.echo(f"      transport: {transport}")
            else:
                command = target or ""
                args = list(cmd_args)
                if not args and " " in command:
                    parts = shlex.split(command)
                    command = parts[0]
                    args = parts[1:]
                click.echo(f"      command: {command}")
                if args:
                    click.echo(f"      args: {args}")

        except Exception as e:
            click.echo(f"Error connecting to MCP server: {e}", err=True)
            sys.exit(1)

    asyncio.run(_inspect())


@mcp.command("list-servers")
def mcp_list_servers() -> None:
    """List commonly used MCP servers.

    Shows a curated list of popular MCP servers that can be used with sandboxy.
    """
    servers = [
        (
            "@modelcontextprotocol/server-filesystem",
            "File system access",
            "npx -y @modelcontextprotocol/server-filesystem <path>",
        ),
        (
            "@modelcontextprotocol/server-github",
            "GitHub API access",
            "npx -y @modelcontextprotocol/server-github",
        ),
        (
            "@modelcontextprotocol/server-postgres",
            "PostgreSQL database",
            "npx -y @modelcontextprotocol/server-postgres <connection-string>",
        ),
        (
            "@modelcontextprotocol/server-sqlite",
            "SQLite database",
            "npx -y @modelcontextprotocol/server-sqlite <db-path>",
        ),
        (
            "@modelcontextprotocol/server-brave-search",
            "Brave Search API",
            "npx -y @modelcontextprotocol/server-brave-search",
        ),
        (
            "@modelcontextprotocol/server-puppeteer",
            "Browser automation",
            "npx -y @modelcontextprotocol/server-puppeteer",
        ),
    ]

    click.echo("Popular MCP Servers:")
    click.echo("")

    for name, desc, cmd in servers:
        click.echo(f"  {name}")
        click.echo(f"    {desc}")
        click.echo(f"    Usage: {cmd}")
        click.echo("")

    click.echo("Inspect a server's tools:")
    click.echo('  sandboxy mcp inspect "npx -y @modelcontextprotocol/server-filesystem /tmp"')
    click.echo("")
    click.echo("More servers: https://github.com/modelcontextprotocol/servers")


if __name__ == "__main__":
    main()
