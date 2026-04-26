"""
agent/exceptions.py
-------------------
Domain exceptions raised by the agent loop.

These are caught by services/agent_service.py which logs them with
enough context to diagnose the failure mode without leaking SDK internals
up to the HTTP layer.
"""


class AgentLoopError(Exception):
    """Raised when the agentic loop exceeds the configured iteration cap."""
    def __init__(self, iterations: int) -> None:
        self.iterations = iterations
        super().__init__(
            f"Agent loop aborted after {iterations} iterations — "
            "possible hallucination cycle."
        )


class AgentTimeoutError(Exception):
    """Raised when the Anthropic API call exceeds the configured timeout."""
    def __init__(self) -> None:
        super().__init__("Anthropic API call timed out.")


class AgentContextError(Exception):
    """Raised when the conversation history exceeds the model's context window."""
    def __init__(self) -> None:
        super().__init__(
            "Conversation history exceeded the model's context window. "
            "Reduce TEAMS_MESSAGE_LIMIT or AGENT_MAX_ITERATIONS."
        )
