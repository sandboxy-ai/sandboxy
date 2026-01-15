# Sandboxy

Open-source framework for developing, testing, and benchmarking AI agents in simulated environments.

## What is Sandboxy?
<img width="1560" height="436" alt="image" src="https://github.com/user-attachments/assets/428fda5f-3078-406c-a99e-59b605d10c12" />


Sandboxy provides a local development environment for building and testing AI agent scenarios. Define scenarios in YAML, run them against any LLM, and evaluate the results.

**Use cases:**
- **Agent Development** - Build and iterate on AI agent behaviors locally
- **Evaluation & Testing** - Run scenarios against models and score their performance
- **Dataset Benchmarking** - Test models against datasets of cases with parallel execution
- **Red-teaming** - Test for prompt injection, policy violations, and edge cases

## Quick Start

### Installation

```bash
# Using uv (recommended)
pip install uv
uv pip install sandboxy

# Or with pip
pip install sandboxy
```

### Set up API keys

```bash
# Add your API key (OpenRouter gives access to 400+ models)
echo "OPENROUTER_API_KEY=your-key-here" >> .env
```

### Initialize a project

```bash
mkdir my-evals && cd my-evals
sandboxy init
```

This creates:
```
my-evals/
├── scenarios/     # Your scenario YAML files
├── tools/         # Custom tool definitions
├── agents/        # Agent configurations (optional)
├── datasets/      # Test case datasets
└── runs/          # Output from runs
```

### Run a scenario

```bash
# Run with a specific model
sandboxy run scenarios/my_scenario.yml -m openai/gpt-4o

# Compare multiple models
sandboxy run scenarios/my_scenario.yml -m openai/gpt-4o -m anthropic/claude-3.5-sonnet

# Run against a dataset
sandboxy run scenarios/my_scenario.yml --dataset datasets/cases.yml -m openai/gpt-4o
```

### Local development UI

```bash
# Start the local dev server with UI
sandboxy open
```

Opens a browser with a local UI for browsing scenarios, running them, and viewing results.

## Writing Scenarios

Scenarios are YAML files that define agent interactions:

```yaml
id: customer-support
name: "Customer Support Test"
description: "Test how an agent handles a refund request"

system_prompt: |
  You are a customer support agent for TechCo.
  Be helpful but follow company policy.

user_prompt: |
  I want a refund for my purchase. Order #12345.

# Define tools the agent can use
tools:
  - name: lookup_order
    description: "Look up order details"
    params:
      order_id:
        type: string
        required: true
    returns: "Order details for {{order_id}}"

# Evaluation criteria
goals:
  - name: acknowledged_request
    description: "Agent acknowledged the refund request"
    check:
      type: contains
      value: "refund"

  - name: looked_up_order
    description: "Agent used the lookup tool"
    check:
      type: tool_called
      tool: lookup_order

scoring:
  max_score: 100
```

## CLI Reference

```bash
# Run scenarios
sandboxy run <file.yml> -m <model>           # Run a scenario
sandboxy run <file.yml> -m <model> --runs 5  # Multiple runs
sandboxy run <file.yml> --dataset <data.yml> # Run against dataset

# Development
sandboxy open                    # Start local UI
sandboxy serve                   # API server only (no browser)
sandboxy init                    # Initialize project structure

# Scaffolding
sandboxy new scenario <name>     # Create scenario template
sandboxy new tool <name>         # Create tool library template

# Information
sandboxy list-models             # List available models
sandboxy list-tools              # List available tool libraries
sandboxy info <file.yml>         # Show scenario details

# MCP Integration
sandboxy mcp inspect <command>   # Inspect MCP server tools
sandboxy mcp list                # List known MCP servers
```

## Models

Sandboxy supports 400+ models via OpenRouter, plus direct provider access:

```bash
# OpenRouter models (recommended)
sandboxy run scenario.yml -m openai/gpt-4o
sandboxy run scenario.yml -m anthropic/claude-3.5-sonnet
sandboxy run scenario.yml -m google/gemini-pro
sandboxy run scenario.yml -m meta-llama/llama-3-70b

# List available models
sandboxy list-models
sandboxy list-models --search claude
sandboxy list-models --free
```

## Configuration

Environment variables (in `~/.sandboxy/.env` or project `.env`):

| Variable | Description |
|----------|-------------|
| `OPENROUTER_API_KEY` | OpenRouter API key (400+ models) |
| `OPENAI_API_KEY` | Direct OpenAI access |
| `ANTHROPIC_API_KEY` | Direct Anthropic access |

## Project Structure

```
sandboxy/
├── sandboxy/           # Python package
│   ├── core/           # Runner, state management
│   ├── scenarios/      # Unified scenario runner
│   ├── datasets/       # Dataset benchmarking
│   ├── agents/         # Agent loading and execution
│   ├── tools/          # Tool loading (YAML tools)
│   ├── providers/      # LLM provider integrations
│   ├── api/            # Local dev API server
│   ├── cli/            # Command-line interface
│   ├── local/          # Local project context
│   └── mcp/            # MCP client integration
└── local-ui/           # Local development UI (React)
```

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 - see [LICENSE](LICENSE).
