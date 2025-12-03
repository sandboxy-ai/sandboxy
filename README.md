# Sandboxy

Open-source agent simulation and benchmarking platform.

## Features

- **MDL (Module Definition Language)** - Define agent evaluation scenarios in YAML
- **BYOA (Bring Your Own Agent)** - Plug in any LLM-based or custom agent
- **Fake Tools** - Mock implementations of Shopify, browser, email for safe testing
- **Benchmarking** - Compare multiple agents on the same scenario
- **Web UI** - Visual interface for running modules and viewing replays

## Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
# Install from source
git clone https://github.com/sandboxy-ai/sandboxy.git
cd sandboxy
uv sync

# Or install with dev dependencies
uv sync --dev
```

Using pip:

```bash
pip install sandboxy

# Or from source
git clone https://github.com/sandboxy-ai/sandboxy.git
cd sandboxy
pip install -e ".[dev]"
```

## Quick Start

### Run a module with an agent

```bash
sandboxy run modules/shopify_refund_v1.yml --agent-id gpt5
```

### Validate an MDL module

```bash
sandboxy validate modules/shopify_refund_v1.yml
```

### Benchmark multiple agents

```bash
sandboxy bench modules/shopify_refund_v1.yml \
  --agents gpt5,gpt5-nano \
  --runs-per-agent 5 \
  --output results.csv
```

## Project Structure

```
sandboxy/           # Python package
├── core/           # MDL parser, runner, state models
├── agents/         # Agent interface and implementations
├── tools/          # Tool interface and fake tools
└── cli/            # Command-line interface

modules/            # Example MDL scenarios (YAML)
agents/             # Agent configuration specs (YAML)
tools/              # Tool configuration specs (YAML)
runs/               # Saved logs and replays
webui/              # Node.js web interface
tests/              # Test suite
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - Required for LLM-based agents using OpenAI models

## License

Apache 2.0
