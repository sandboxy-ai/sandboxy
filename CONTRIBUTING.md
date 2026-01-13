# Contributing to Sandboxy

Thank you for your interest in contributing to Sandboxy! This document provides guidelines for contributing.

## Ways to Contribute

- **Bug Reports** - Found a bug? Open an issue with reproduction steps
- **Feature Requests** - Have an idea? Open an issue to discuss
- **Scenarios** - Create new test scenarios and submit a PR
- **Tool Libraries** - Build YAML tool definitions for new use cases
- **Documentation** - Improve docs, add examples, fix typos
- **Code** - Fix bugs, add features, improve performance

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

```bash
# Clone the repo
git clone https://github.com/sandboxy-ai/sandboxy.git
cd sandboxy

# Install dependencies
uv sync --dev

# Set up environment
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
```

### Running Locally

```bash
# Start local dev server with UI
sandboxy open

# Or run scenarios directly
sandboxy run scenarios/example.yml -m openai/gpt-4o
```

## Code Style

### Python

- Use [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- Follow PEP 8
- Add type hints to all functions
- Write docstrings for public APIs

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Run tests
pytest
```

## Creating Scenarios

Scenarios live in `scenarios/` as YAML files. See existing scenarios for examples.

### Scenario Guidelines

1. **Clear description** - Explain what the scenario tests
2. **Meaningful goals** - Include checks that measure agent performance
3. **Good defaults** - Work out of the box without configuration
4. **Documentation** - Include comments explaining complex parts

### Example Scenario

```yaml
id: my-scenario
name: "My Test Scenario"
description: "Tests agent behavior in X situation"

system_prompt: |
  You are a helpful assistant.

user_prompt: |
  Help me with this task.

goals:
  - name: completed_task
    description: "Agent completed the task"
    check:
      type: contains
      value: "done"

scoring:
  max_score: 100
```

### Testing Your Scenario

```bash
# Run with a model
sandboxy run scenarios/my_scenario.yml -m openai/gpt-4o

# Compare models
sandboxy run scenarios/my_scenario.yml -m openai/gpt-4o -m anthropic/claude-3.5-sonnet
```

## Creating Tool Libraries

Tool libraries are YAML files that define tools agents can use. Place them in your project's `tools/` directory.

### Tool Library Guidelines

1. **Clear actions** - Each tool action should have a clear purpose
2. **Good descriptions** - Help the agent understand what tools do
3. **Sensible returns** - Return useful information
4. **Side effects** - Use side_effects to update state

### Example Tool Library

```yaml
name: mock_inventory
description: "Inventory management tools"

tools:
  check_stock:
    description: "Check stock level for an item"
    params:
      item_id:
        type: string
        required: true
    returns: "Stock level for {{item_id}}: 50 units"

  update_stock:
    description: "Update stock level"
    params:
      item_id:
        type: string
        required: true
      quantity:
        type: number
        required: true
    returns: "Updated {{item_id}} to {{quantity}} units"
    side_effects:
      - set: "stock_{{item_id}}"
        value: "{{quantity}}"
```

Use in scenarios with:

```yaml
tools_from:
  - mock_inventory
```

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature/fix
3. **Make changes** following the code style guidelines
4. **Write tests** if applicable
5. **Update documentation** if needed
6. **Submit a PR** with a clear description

### PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally
- [ ] Documentation updated
- [ ] No secrets or API keys committed

## Questions?

- Open an issue for questions

Thank you for contributing!
