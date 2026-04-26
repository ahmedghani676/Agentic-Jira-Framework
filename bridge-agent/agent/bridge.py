"""
agent/bridge.py
---------------
Bridge Agent — core agentic loop.

Two-phase design
----------------
1. process()  — runs Claude + tools in DRY-RUN mode.
                Returns a list of DecisionItem objects for the admin to review.
                Nothing is written to Jira or Teams.

2. submit()   — executes the approved decisions against the real APIs.
                Mutates each DecisionItem.submitted / submitted_jira_key in place.
"""

import json
import logging
from dataclasses import dataclass

import anthropic

import clients.hubspot as hubspot
import clients.jira as jira
import clients.teams as teams
from agent.exceptions import AgentContextError, AgentLoopError, AgentTimeoutError
from agent.prompts import SYSTEM_PROMPT
from agent.tools import TOOLS
from config import settings
from models import DecisionItem

logger = logging.getLogger(__name__)

_anthropic = anthropic.Anthropic(
    api_key=settings.anthropic_api_key,
    timeout=settings.agent_timeout_seconds,
    max_retries=3,
)


# ---------------------------------------------------------------------------
# Run cache — separates caching concern from tool dispatch
# ---------------------------------------------------------------------------

@dataclass
class _RunCache:
    """Holds API responses fetched once per process run."""
    messages: list[dict] | None = None
    backlog: list[dict] | None = None


# ---------------------------------------------------------------------------
# Tool dispatcher — dry-run only; records decisions for admin review
# ---------------------------------------------------------------------------

class ToolDispatcher:
    """
    Executes Claude's tool calls during the dry-run phase.
    Records one DecisionItem per Teams message. Never writes to external APIs.

    Each action tool (create_jira_ticket, add_jira_comment, send_teams_feedback)
    carries message_id, client_name, and arr explicitly so decisions are correctly
    tracked per-message even when Claude batches tool calls in a single turn.
    """

    def __init__(self) -> None:
        self.decisions: list[DecisionItem] = []
        self._cache = _RunCache()

    # ------------------------------------------------------------------
    # Dispatcher entry point
    # ------------------------------------------------------------------

    def dispatch(self, name: str, inputs: dict) -> str:
        """Route a tool call to its handler and return a JSON string result."""
        handler = getattr(self, f"_tool_{name}", None)
        if handler is None:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            return handler(inputs)
        except Exception as exc:
            logger.exception("Tool '%s' raised an exception", name)
            return json.dumps({"error": str(exc)})

    # ------------------------------------------------------------------
    # Tool handlers
    # ------------------------------------------------------------------

    def _tool_get_teams_messages(self, inputs: dict) -> str:
        if self._cache.messages is None:
            limit = inputs.get("limit", settings.teams_message_limit)
            self._cache.messages = [m.model_dump() for m in teams.get_messages(limit=limit)]
        return json.dumps(self._cache.messages)

    def _tool_get_jira_backlog(self, inputs: dict) -> str:
        if self._cache.backlog is None:
            self._cache.backlog = [i.model_dump() for i in jira.search_issues(max_results=100)]
        return json.dumps(self._cache.backlog)

    def _tool_search_hubspot_company(self, inputs: dict) -> str:
        name: str = inputs["company_name"]
        arr = hubspot.get_arr(name)
        return json.dumps({"company_name": name, "arr": arr})

    def _tool_create_jira_ticket(self, inputs: dict) -> str:
        decision = self._get_or_create_decision(
            message_id=inputs["message_id"],
            client_name=inputs.get("client_name", "Unknown"),
            arr=inputs.get("arr"),
            action="CREATE",
        )
        decision.draft_summary = inputs["summary"]
        decision.draft_description = inputs["description"]
        decision.draft_labels = inputs.get("labels", [])
        return json.dumps({
            "dry_run": True,
            "planned_action": "CREATE",
            "summary": inputs["summary"],
        })

    def _tool_add_jira_comment(self, inputs: dict) -> str:
        decision = self._get_or_create_decision(
            message_id=inputs["message_id"],
            client_name=inputs.get("client_name", "Unknown"),
            arr=inputs.get("arr"),
            action="UPDATE",
        )
        decision.jira_key = inputs["issue_key"]
        decision.draft_comment = inputs["comment"]
        return json.dumps({
            "dry_run": True,
            "planned_action": "UPDATE",
            "issue_key": inputs["issue_key"],
        })

    def _tool_send_teams_feedback(self, inputs: dict) -> str:
        decision = self._get_or_create_decision(
            message_id=inputs["message_id"],
            client_name=None,
            arr=None,
            action=None,
        )
        decision.teams_feedback = inputs["message"]
        return json.dumps({"dry_run": True, "planned_message": inputs["message"]})

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _lookup_message(self, message_id: str) -> dict:
        """Find a cached Teams message by its id field."""
        if self._cache.messages:
            for m in self._cache.messages:
                if m.get("id") == message_id:
                    return m
        return {"id": message_id, "sender": "Unknown", "text": ""}

    def _get_or_create_decision(
        self,
        message_id: str,
        client_name: str | None,
        arr: int | None,
        action: str | None,
    ) -> DecisionItem:
        """
        Return the existing DecisionItem for message_id or create one.
        Upgrades action priority: CREATE/UPDATE > SKIP.
        """
        for d in self.decisions:
            if d.message_id == message_id:
                if action and d.action == "SKIP":
                    d.action = action  # type: ignore[assignment]
                return d

        msg = self._lookup_message(message_id)
        d = DecisionItem(
            message_id=message_id,
            sender=msg.get("sender", "Unknown"),
            message_text=msg.get("text", ""),
            client_name=client_name or "Unknown",
            core_request="",
            arr=arr,
            action=action or "SKIP",  # type: ignore[arg-type]
        )
        self.decisions.append(d)
        return d


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process() -> list[DecisionItem]:
    """
    Phase 1 — Dry-run.
    Runs the Claude agent loop, records all decisions, returns them for review.
    No writes to Jira or Teams occur.
    """
    dispatcher = ToolDispatcher()
    _run_agent(dispatcher)
    return dispatcher.decisions


def submit(decisions: list[DecisionItem]) -> list[DecisionItem]:
    """
    Phase 2 — Execute.
    Writes each non-SKIP decision to Jira (create/comment) and Teams (feedback).
    Mutates DecisionItem.submitted / submitted_jira_key in place.
    """
    for d in decisions:
        if d.action == "SKIP":
            continue
        try:
            if d.action == "CREATE" and d.draft_summary:
                result = jira.create_issue(
                    summary=d.draft_summary,
                    description=d.draft_description or "",
                    labels=d.draft_labels,
                )
                d.submitted_jira_key = result.key

            elif d.action == "UPDATE" and d.jira_key and d.draft_comment:
                jira.add_comment(d.jira_key, d.draft_comment)
                d.submitted_jira_key = d.jira_key

            if d.teams_feedback:
                feedback = d.teams_feedback
                if d.submitted_jira_key:
                    feedback = feedback.replace("JIRA-???", d.submitted_jira_key)
                teams.send_message(feedback)

            d.submitted = True

        except Exception:
            logger.exception(
                "Failed to submit decision for message_id=%s action=%s",
                d.message_id,
                d.action,
            )

    return decisions


# ---------------------------------------------------------------------------
# Internal agent loop
# ---------------------------------------------------------------------------

def _run_agent(dispatcher: ToolDispatcher) -> None:
    """
    Agentic loop: keeps sending tool results back to Claude until end_turn.

    Raises
    ------
    AgentLoopError:    loop exceeded AGENT_MAX_ITERATIONS (hallucination cycle).
    AgentTimeoutError: Anthropic API call timed out.
    AgentContextError: conversation history exceeded the model's context window.
    """
    messages: list[dict] = [
        {
            "role": "user",
            "content": "Process all feature-request messages from Teams now.",
        }
    ]

    for iteration in range(1, settings.agent_max_iterations + 1):
        logger.debug("Agent loop iteration %d/%d", iteration, settings.agent_max_iterations)

        try:
            response = _anthropic.messages.create(
                model=settings.claude_model,
                max_tokens=8192,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )
        except anthropic.APITimeoutError as exc:
            raise AgentTimeoutError() from exc
        except anthropic.BadRequestError as exc:
            if "context_length_exceeded" in str(exc) or "too many tokens" in str(exc).lower():
                raise AgentContextError() from exc
            raise

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            logger.info("Agent loop finished normally after %d iterations", iteration)
            return

        if response.stop_reason != "tool_use":
            logger.warning("Unexpected stop_reason=%s — stopping loop", response.stop_reason)
            return

        tool_results: list[dict] = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            logger.info("Tool call → %s(%s)", block.name, json.dumps(block.input)[:120])
            result_str = dispatcher.dispatch(block.name, block.input)
            logger.debug("Tool result ← %s", result_str[:200])
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str,
            })

        messages.append({"role": "user", "content": tool_results})

    raise AgentLoopError(settings.agent_max_iterations)
