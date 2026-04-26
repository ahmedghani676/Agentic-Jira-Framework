"""
services/agent_service.py
--------------------------
Business logic layer for the Bridge Agent.

This service sits between the HTTP route controllers (routes/agent.py) and the
lower-level agent loop (agent/bridge.py) + session store (store/session.py).

Responsibilities
----------------
- Orchestrate a full process run: call the agent, generate a run_id, persist decisions.
- Orchestrate a full submit run: validate state, execute decisions, return results.
- Retrieve an existing run by ID.
- Own all decision about run_id generation, duplicate-submission checks, and
  counting submitted actions.

What this service does NOT do
------------------------------
- Handle HTTP concerns (status codes, request parsing, response serialisation).
  Those belong in routes/agent.py.
- Execute low-level API calls (Jira, HubSpot, Teams).
  Those belong in clients/ and are called by agent/bridge.py.
"""

import logging
import uuid

from agent.bridge import process, submit
from agent.exceptions import AgentContextError, AgentLoopError, AgentTimeoutError
from models import DecisionItem, ProcessResponse, RunResponse, SubmitResponse
from models import DecisionResponse
from store.session import session_store

logger = logging.getLogger(__name__)


class RunNotFoundError(Exception):
    """Raised when a run_id does not exist in the session store."""
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"run_id '{run_id}' not found.")


class RunAlreadySubmittedError(Exception):
    """Raised when a submit is attempted on an already-executed run."""
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        super().__init__(f"run_id '{run_id}' has already been submitted.")


class AgentService:
    """
    Orchestrates dry-run and submit workflows for the Bridge Agent.

    The route layer calls these methods and maps any raised service
    exceptions to the appropriate HTTP status codes.
    """

    def process_messages(self) -> ProcessResponse:
        """
        Run the Claude agent in dry-run mode over all Teams messages.

        Steps
        -----
        1. Invoke the agent loop — fetches Teams messages, cross-references
           HubSpot ARR, checks Jira for duplicates, drafts decisions.
        2. Generate a unique run_id for this batch.
        3. Persist decisions in the session store.
        4. Return a fully built ProcessResponse.

        Returns
        -------
        ProcessResponse with run_id, total count, and per-message decisions.

        Raises
        ------
        Exception: Re-raised from agent.bridge.process() on unexpected failure.
        """
        logger.info("AgentService: starting process run")
        try:
            decisions: list[DecisionItem] = process()
        except AgentTimeoutError:
            logger.error("AgentService: Anthropic API timed out during process run")
            raise
        except AgentLoopError as exc:
            logger.error("AgentService: agent loop aborted after %d iterations", exc.iterations)
            raise
        except AgentContextError:
            logger.error("AgentService: context window exceeded — reduce TEAMS_MESSAGE_LIMIT")
            raise

        run_id = str(uuid.uuid4())
        session_store.save(run_id, decisions)

        logger.info(
            "AgentService: process run %s complete — %d decisions",
            run_id,
            len(decisions),
        )
        return ProcessResponse(
            run_id=run_id,
            total=len(decisions),
            decisions=[DecisionResponse.from_decision(d) for d in decisions],
        )

    def submit_decisions(self, run_id: str) -> SubmitResponse:
        """
        Execute all approved (non-SKIP) decisions from a previous process run.

        Steps
        -----
        1. Retrieve the pending decisions from the session store.
        2. Guard against unknown or already-submitted run_ids.
        3. Execute each decision: CREATE → Jira issue, UPDATE → Jira comment,
           then post a Teams confirmation message.
        4. Count successfully submitted actions.
        5. Return a fully built SubmitResponse.

        Args
        ----
        run_id: The run identifier returned by a previous process_messages() call.

        Returns
        -------
        SubmitResponse with run_id, submitted count, and updated decisions.

        Raises
        ------
        RunNotFoundError:        run_id does not exist in the session store.
        RunAlreadySubmittedError: decisions for this run were already executed.
        Exception:               Re-raised from agent.bridge.submit() on unexpected failure.
        """
        decisions = session_store.get(run_id)
        if decisions is None:
            raise RunNotFoundError(run_id)

        if any(d.submitted for d in decisions):
            raise RunAlreadySubmittedError(run_id)

        logger.info(
            "AgentService: submitting run %s (%d decisions)",
            run_id,
            len(decisions),
        )
        updated = submit(decisions)
        submitted_count = sum(1 for d in updated if d.submitted)

        logger.info(
            "AgentService: run %s submitted — %d/%d actions executed",
            run_id,
            submitted_count,
            len(updated),
        )
        return SubmitResponse(
            run_id=run_id,
            submitted=submitted_count,
            decisions=[DecisionResponse.from_decision(d) for d in updated],
        )

    def get_run(self, run_id: str) -> RunResponse:
        """
        Retrieve the decisions for an existing run without re-running the agent.

        Args
        ----
        run_id: The run identifier to look up.

        Returns
        -------
        RunResponse with run_id, total count, and all decisions.

        Raises
        ------
        RunNotFoundError: run_id does not exist in the session store.
        """
        decisions = session_store.get(run_id)
        if decisions is None:
            raise RunNotFoundError(run_id)

        return RunResponse(
            run_id=run_id,
            total=len(decisions),
            decisions=[DecisionResponse.from_decision(d) for d in decisions],
        )


# Module-level singleton — imported by routes/agent.py.
agent_service = AgentService()
