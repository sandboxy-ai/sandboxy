"""Mock browser tool for testing web browsing scenarios."""

from typing import Any

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class MockBrowserTool(BaseTool):
    """Mock browser with canned pages for testing."""

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)
        # Initialize with default pages or from config
        self.pages: dict[str, str] = self.config.get("pages", {
            "https://example.com": "<html><body><h1>Example Domain</h1></body></html>",
            "https://example.com/policy": (
                "Refund Policy: Refunds are allowed within 30 days of purchase. "
                "Items must be in original condition. Digital products are non-refundable."
            ),
            "https://example.com/faq": (
                "FAQ:\n"
                "Q: How do I track my order?\n"
                "A: Use the tracking number sent to your email.\n\n"
                "Q: What is your return policy?\n"
                "A: Items can be returned within 30 days."
            ),
            "https://example.com/contact": (
                "Contact Us:\n"
                "Email: support@example.com\n"
                "Phone: 1-800-EXAMPLE\n"
                "Hours: Mon-Fri 9AM-5PM EST"
            ),
        })
        self.current_url: str | None = None
        self.history: list[str] = []

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle browser actions."""
        handlers = {
            "open": self._open,
            "navigate": self._open,  # Alias
            "get_content": self._get_content,
            "search": self._search,
            "back": self._back,
            "get_current_url": self._get_current_url,
        }

        handler = handlers.get(action)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        return handler(args, env_state)

    def _open(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Open a URL and return its content."""
        url = args.get("url")
        if not url:
            return ToolResult(success=False, error="url is required")

        content = self.pages.get(url)
        if content is None:
            return ToolResult(
                success=False,
                error=f"Page not found: {url}",
                data={"status_code": 404},
            )

        if self.current_url:
            self.history.append(self.current_url)
        self.current_url = url

        return ToolResult(
            success=True,
            data={
                "url": url,
                "content": content,
                "status_code": 200,
            },
        )

    def _get_content(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get content of current page."""
        if not self.current_url:
            return ToolResult(success=False, error="No page is currently open")

        content = self.pages.get(self.current_url)
        return ToolResult(
            success=True,
            data={
                "url": self.current_url,
                "content": content,
            },
        )

    def _search(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Search for text within available pages."""
        query = args.get("query", "").lower()
        if not query:
            return ToolResult(success=False, error="query is required")

        results = []
        for url, content in self.pages.items():
            if query in content.lower():
                # Return snippet around the match
                lower_content = content.lower()
                idx = lower_content.find(query)
                start = max(0, idx - 50)
                end = min(len(content), idx + len(query) + 50)
                snippet = content[start:end]
                if start > 0:
                    snippet = "..." + snippet
                if end < len(content):
                    snippet = snippet + "..."
                results.append({"url": url, "snippet": snippet})

        return ToolResult(
            success=True,
            data={"query": query, "results": results, "count": len(results)},
        )

    def _back(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Go back to previous page."""
        if not self.history:
            return ToolResult(success=False, error="No history to go back to")

        previous_url = self.history.pop()
        self.current_url = previous_url
        content = self.pages.get(previous_url, "")

        return ToolResult(
            success=True,
            data={
                "url": previous_url,
                "content": content,
            },
        )

    def _get_current_url(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Get the current URL."""
        return ToolResult(
            success=True,
            data={"url": self.current_url},
        )

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available browser actions."""
        return [
            {
                "name": "open",
                "description": "Open a URL and return its content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to open"},
                    },
                    "required": ["url"],
                },
            },
            {
                "name": "get_content",
                "description": "Get the content of the current page",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "search",
                "description": "Search for text within available pages",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Text to search for"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "back",
                "description": "Go back to the previous page",
                "parameters": {"type": "object", "properties": {}},
            },
            {
                "name": "get_current_url",
                "description": "Get the currently open URL",
                "parameters": {"type": "object", "properties": {}},
            },
        ]
