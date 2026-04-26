"""
store/session.py
----------------
In-memory session store for agent dry-run results.

SessionStore maps a run_id (UUID string) to the list of DecisionItems
produced by a process() call. The submit() call later retrieves and
mutates those same objects.

Production note
---------------
This implementation uses a plain Python dict and is therefore
single-process only. In a multi-worker or serverless deployment,
replace the dict with a Redis or PostgreSQL-backed store while keeping
the same SessionStore interface.
"""

from models import DecisionItem


class SessionStore:
    """
    Thin wrapper around an in-memory dict of { run_id: list[DecisionItem] }.

    Keeping this in its own class rather than a bare module-level dict makes
    it straightforward to swap the backing store without touching route code.
    """

    def __init__(self) -> None:
        self._store: dict[str, list[DecisionItem]] = {}

    def save(self, run_id: str, decisions: list[DecisionItem]) -> None:
        """
        Persist a list of decisions under the given run_id.

        Args:
            run_id:    Unique identifier for this agent run.
            decisions: Decisions produced by agent.bridge.process().
        """
        self._store[run_id] = decisions

    def get(self, run_id: str) -> list[DecisionItem] | None:
        """
        Retrieve decisions for a run, or None if the run_id is unknown.

        Args:
            run_id: The run identifier returned by a previous process() call.

        Returns:
            List of DecisionItems, or None if not found.
        """
        return self._store.get(run_id)

    def exists(self, run_id: str) -> bool:
        """Return True if the run_id has a stored session."""
        return run_id in self._store


# Module-level singleton — imported by routes that need the store.
session_store = SessionStore()
