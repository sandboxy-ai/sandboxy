.PHONY: dev install clean build-local-ui test fmt lint help

# Run the local dev server
dev:
	@echo "Starting Sandboxy local server..."
	uv run sandboxy open

# Run the local UI dev server (for UI development with hot reload)
# Use with: sandboxy open (in another terminal) + open http://localhost:5174
local-ui-dev:
	@echo "Starting local UI dev server with hot reload..."
	@echo "1. Run 'sandboxy open' in another terminal (API backend)"
	@echo "2. Open http://localhost:5174 in your browser (hot-reload UI)"
	@echo ""
	cd local-ui && npm install && npm run dev

# Install all dependencies
install:
	@echo "Installing Python dependencies..."
	uv sync
	@echo "Installing local-ui dependencies..."
	cd local-ui && npm install

# Build the local UI for bundling with pip package
build-local-ui:
	@echo "Building local UI..."
	cd local-ui && npm install && npm run build
	@echo "Local UI built to sandboxy/ui/dist/"

# Clean build artifacts
clean:
	rm -rf local-ui/node_modules/.vite
	rm -rf sandboxy/ui/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/

# Run tests
test:
	uv run pytest

# Format code
fmt:
	uv run ruff format .

# Lint code
lint:
	uv run ruff check .

# Help
help:
	@echo "Available targets:"
	@echo "  dev           - Run local dev server with UI"
	@echo "  local-ui-dev  - Run local UI dev server (for UI development)"
	@echo "  install       - Install all dependencies"
	@echo "  build-local-ui- Build local UI for pip package"
	@echo "  clean         - Clean build artifacts"
	@echo "  test          - Run tests"
	@echo "  fmt           - Format code"
	@echo "  lint          - Lint code"
