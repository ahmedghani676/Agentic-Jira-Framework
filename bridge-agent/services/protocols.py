"""
services/protocols.py
---------------------
Structural interface for the agent service layer.

Routes depend on AgentServiceProtocol, not the concrete AgentService class.
This keeps the controller decoupled from any specific implementation and
makes the service trivially swappable in tests via FastAPI's Depends.
"""

from typing import Protocol

from models import ProcessResponse, RunResponse, SubmitResponse


class AgentServiceProtocol(Protocol):
    def process_messages(self) -> ProcessResponse: ...
    def submit_decisions(self, run_id: str) -> SubmitResponse: ...
    def get_run(self, run_id: str) -> RunResponse: ...
