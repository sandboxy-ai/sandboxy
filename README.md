# Sandboxy

Open-source platform for testing and benchmarking AI agents in controlled, simulated environments.

## What is Sandboxy?

Sandboxy lets you run AI agents through simulated scenarios to:

- **Security Testing** - Test for prompt injection, social engineering vulnerabilities, and policy violations
- **Benchmarking** - Compare AI models head-to-head with numeric scores
- **Interactive Play** - Watch agents handle chaos, inject events, and create shareable content

## Features

- **MDL (Module Definition Language)** - Define scenarios in YAML with variables, steps, tools, and evaluation
- **BYOA (Bring Your Own Agent)** - Plug in OpenAI, Anthropic, or custom agents
- **Mock Tools** - Simulated systems (stores, email, browsers, games) for safe testing
- **Event Injection** - Inject chaos mid-scenario to test agent adaptability
- **Scoring System** - Custom formulas with normalization for fair comparison
- **Web UI** - React-based interface for running scenarios and viewing results
- **CLI** - Run benchmarks programmatically with CSV/JSON export

## Scenarios Included

| Scenario | Description | Use Case |
|----------|-------------|----------|
| **Lemonade Stand** | Run a lemonade business with inventory, weather, and events | Gaming/Benchmarking |
| **Negotiation Arena** | Haggle for discounts without violating policies | Security/Gaming |
| **Break the Bank** | Exploit refund policies (red-team) | Security Testing |
| **Wedding Planner** | Handle bridezilla demands within budget | Entertainment/Viral |
| **Social Engineering** | Defend secrets from manipulation | Security Testing |

## Quick Start

### Installation

Using [uv](https://docs.astral.sh/uv/) (recommended):

```bash
git clone https://github.com/sandboxy-ai/sandboxy.git
cd sandboxy
uv sync
```

Using pip:

```bash
pip install sandboxy
```

### Set up API keys

```bash
export OPENAI_API_KEY=your-key-here
# or
export ANTHROPIC_API_KEY=your-key-here
```

### Run a scenario

```bash
# Interactive mode with web UI
sandboxy-server

# CLI mode
sandboxy run modules/lemonade_stand_v1.yml --agent-id gpt4
```

### Benchmark multiple agents

```bash
sandboxy bench modules/lemonade_stand_v1.yml \
  --agents gpt4,claude,gpt35 \
  --runs-per-agent 5 \
  --output results.csv
```

## Project Structure

```
sandboxy/
├── sandboxy/           # Python package
│   ├── core/           # MDL parser, runners, state models
│   ├── agents/         # Agent interface and LLM implementations
│   ├── tools/          # Tool interface and mock tools
│   ├── api/            # FastAPI server and WebSocket
│   ├── session/        # Session management
│   ├── db/             # SQLite database
│   └── cli/            # Command-line interface
├── frontend/           # React/TypeScript web UI
├── modules/            # Scenario definitions (YAML)
├── agents/             # Agent configurations (YAML)
└── work/               # Development docs
```

## Creating Scenarios

Scenarios are defined in YAML using MDL:

```yaml
id: My Scenario
description: A simple example scenario

variables:
  - name: difficulty
    type: slider
    min: 1
    max: 10
    default: 5

agent:
  system_prompt: |
    You are a helpful assistant.
    Difficulty level: {{difficulty}}

environment:
  tools:
    - name: calculator
      type: mock_calculator

steps:
  - id: start
    action: inject_user
    params:
      content: "Hello!"

  - id: respond
    action: await_agent
    params: {}

evaluation:
  - name: Responded
    kind: deterministic
    config:
      expr: "len(events) > 0"

scoring:
  formula: "Responded * 100"
  normalize: true
```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key | For OpenAI agents |
| `ANTHROPIC_API_KEY` | Anthropic API key | For Claude agents |
| `SANDBOXY_HOST` | Server host | Default: 0.0.0.0 |
| `SANDBOXY_PORT` | Server port | Default: 8000 |
| `SANDBOXY_DISABLE_RATE_LIMIT` | Disable rate limiting | Default: false |

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run backend
sandboxy-server

# Run frontend (separate terminal)
cd frontend
npm install
npm run dev

# Run tests
pytest
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

Apache License - see [LICENSE](LICENSE) for details.

## Links

- [Documentation](https://sandboxy.ai/docs)
- [GitHub](https://github.com/sandboxy-ai/sandboxy)
- [Discord](https://discord.gg/sandboxy)
