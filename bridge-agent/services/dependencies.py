"""
services/dependencies.py
------------------------
FastAPI dependency providers for the service layer.

Import get_agent_service into route files and declare it via Depends.
The default implementation returns the module-level AgentService singleton,
but any test can override it by calling app.dependency_overrides.
"""

from services.agent_service import agent_service
from services.protocols import AgentServiceProtocol


def get_agent_service() -> AgentServiceProtocol:
    return agent_service
