"""Mock email tool for testing email scenarios."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sandboxy.tools.base import BaseTool, ToolConfig, ToolResult


class MockEmailTool(BaseTool):
    """Mock email service for testing."""

    def __init__(self, config: ToolConfig) -> None:
        super().__init__(config)
        # Initialize with empty mailboxes or from config
        self.sent_emails: list[dict[str, Any]] = []
        self.inbox: list[dict[str, Any]] = self.config.get("initial_inbox", [])
        self.drafts: list[dict[str, Any]] = []

    def invoke(self, action: str, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Handle email actions."""
        handlers = {
            "send": self._send,
            "list_inbox": self._list_inbox,
            "read": self._read,
            "save_draft": self._save_draft,
            "list_sent": self._list_sent,
            "search": self._search,
        }

        handler = handlers.get(action)
        if handler is None:
            return ToolResult(success=False, error=f"Unknown action: {action}")

        return handler(args, env_state)

    def _send(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Send an email."""
        to = args.get("to")
        subject = args.get("subject", "")
        body = args.get("body", "")
        cc = args.get("cc", [])
        bcc = args.get("bcc", [])

        if not to:
            return ToolResult(success=False, error="'to' recipient is required")

        # Validate email format (basic check)
        recipients = [to] if isinstance(to, str) else to
        for recipient in recipients:
            if "@" not in recipient:
                return ToolResult(success=False, error=f"Invalid email address: {recipient}")

        email_id = str(uuid.uuid4())[:8]
        email = {
            "id": email_id,
            "to": recipients,
            "cc": cc,
            "bcc": bcc,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now(UTC).isoformat(),
            "status": "sent",
        }
        self.sent_emails.append(email)

        return ToolResult(
            success=True,
            data={
                "email_id": email_id,
                "status": "sent",
                "recipients": recipients,
            },
        )

    def _list_inbox(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """List emails in inbox."""
        limit = args.get("limit", 10)
        unread_only = args.get("unread_only", False)

        emails = self.inbox
        if unread_only:
            emails = [e for e in emails if not e.get("read", False)]

        emails = emails[:limit]

        # Return summaries, not full content
        summaries = [
            {
                "id": e.get("id"),
                "from": e.get("from"),
                "subject": e.get("subject"),
                "received_at": e.get("received_at"),
                "read": e.get("read", False),
            }
            for e in emails
        ]

        return ToolResult(
            success=True,
            data={"emails": summaries, "count": len(summaries)},
        )

    def _read(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Read a specific email by ID."""
        email_id = args.get("email_id")
        if not email_id:
            return ToolResult(success=False, error="email_id is required")

        # Check inbox
        for email in self.inbox:
            if email.get("id") == email_id:
                email["read"] = True
                return ToolResult(success=True, data=email)

        # Check sent
        for email in self.sent_emails:
            if email.get("id") == email_id:
                return ToolResult(success=True, data=email)

        return ToolResult(success=False, error=f"Email not found: {email_id}")

    def _save_draft(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Save an email as draft."""
        to = args.get("to", [])
        subject = args.get("subject", "")
        body = args.get("body", "")

        draft_id = str(uuid.uuid4())[:8]
        draft = {
            "id": draft_id,
            "to": to if isinstance(to, list) else [to] if to else [],
            "subject": subject,
            "body": body,
            "created_at": datetime.now(UTC).isoformat(),
            "status": "draft",
        }
        self.drafts.append(draft)

        return ToolResult(
            success=True,
            data={"draft_id": draft_id, "status": "saved"},
        )

    def _list_sent(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """List sent emails."""
        limit = args.get("limit", 10)
        emails = self.sent_emails[:limit]

        summaries = [
            {
                "id": e.get("id"),
                "to": e.get("to"),
                "subject": e.get("subject"),
                "sent_at": e.get("sent_at"),
            }
            for e in emails
        ]

        return ToolResult(
            success=True,
            data={"emails": summaries, "count": len(summaries)},
        )

    def _search(self, args: dict[str, Any], env_state: dict[str, Any]) -> ToolResult:
        """Search emails by subject or body content."""
        query = args.get("query", "").lower()
        if not query:
            return ToolResult(success=False, error="query is required")

        results = []

        # Search inbox
        for email in self.inbox:
            if (
                query in email.get("subject", "").lower()
                or query in email.get("body", "").lower()
            ):
                results.append({
                    "id": email.get("id"),
                    "from": email.get("from"),
                    "subject": email.get("subject"),
                    "location": "inbox",
                })

        # Search sent
        for email in self.sent_emails:
            if (
                query in email.get("subject", "").lower()
                or query in email.get("body", "").lower()
            ):
                results.append({
                    "id": email.get("id"),
                    "to": email.get("to"),
                    "subject": email.get("subject"),
                    "location": "sent",
                })

        return ToolResult(
            success=True,
            data={"query": query, "results": results, "count": len(results)},
        )

    def get_actions(self) -> list[dict[str, Any]]:
        """Get available email actions."""
        return [
            {
                "name": "send",
                "description": "Send an email",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {
                            "type": "string",
                            "description": "Recipient email address",
                        },
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                        "cc": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "CC recipients",
                        },
                    },
                    "required": ["to"],
                },
            },
            {
                "name": "list_inbox",
                "description": "List emails in inbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max emails to return"},
                        "unread_only": {"type": "boolean", "description": "Only unread emails"},
                    },
                },
            },
            {
                "name": "read",
                "description": "Read a specific email by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "email_id": {"type": "string", "description": "Email ID to read"},
                    },
                    "required": ["email_id"],
                },
            },
            {
                "name": "save_draft",
                "description": "Save an email as draft",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "description": "Recipient email"},
                        "subject": {"type": "string", "description": "Email subject"},
                        "body": {"type": "string", "description": "Email body"},
                    },
                },
            },
            {
                "name": "list_sent",
                "description": "List sent emails",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Max emails to return"},
                    },
                },
            },
            {
                "name": "search",
                "description": "Search emails by content",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                    },
                    "required": ["query"],
                },
            },
        ]
