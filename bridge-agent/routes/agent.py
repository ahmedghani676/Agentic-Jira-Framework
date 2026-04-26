"""
routes/agent.py
---------------
Bridge Agent HTTP controllers.

Each function here has exactly one job:
  1. Accept and validate the HTTP request.
  2. Delegate to the service layer via dependency injection.
  3. Map service exceptions to HTTP status codes.
  4. Return the HTTP response.

No business logic lives here — run_id generation, session store access,
decision counting, and response building all belong in services/agent_service.py.

POST /api/process   — run the Claude agent in dry-run mode
POST /api/submit    — execute approved decisions against Jira + Teams
GET  /api/runs/{id} — retrieve an existing run by its ID
"""

import logging

from fastapi import APIRouter, Depends, HTTPException

from constants import ErrorMessages, HTTPStatus, OpenAPIResponses, OpenAPITag
from models import ProcessResponse, RunResponse, SubmitRequest, SubmitResponse
from services.dependencies import get_agent_service
from services.agent_service import RunAlreadySubmittedError, RunNotFoundError
from services.protocols import AgentServiceProtocol

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=[OpenAPITag.AGENT])


@router.post(
    "/process",
    response_model=ProcessResponse,
    status_code=HTTPStatus.OK,
    summary="Run agent in dry-run mode",
    description=(
        "Fetches Teams messages, runs the Claude agent, and returns a list of "
        "proposed actions for admin review. **Nothing is written to Jira or Teams yet.**"
    ),
    responses={
        **OpenAPIResponses.UNAUTHORIZED,
        **OpenAPIResponses.INTERNAL_SERVER_ERROR,
    },
)
def run_process(
    service: AgentServiceProtocol = Depends(get_agent_service),
) -> ProcessResponse:
    try:
        return service.process_messages()
    except Exception:
        logger.exception("process_messages() failed")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.PROCESS_FAILED,
        )


@router.post(
    "/submit",
    response_model=SubmitResponse,
    status_code=HTTPStatus.OK,
    summary="Submit approved decisions to Jira and Teams",
    description=(
        "Executes all non-SKIP decisions from a previous `/api/process` run. "
        "Creates or updates Jira tickets and posts Teams confirmation messages. "
        "Can only be called once per run_id."
    ),
    responses={
        **OpenAPIResponses.UNAUTHORIZED,
        **OpenAPIResponses.NOT_FOUND,
        **OpenAPIResponses.CONFLICT,
        **OpenAPIResponses.INTERNAL_SERVER_ERROR,
    },
)
def run_submit(
    body: SubmitRequest,
    service: AgentServiceProtocol = Depends(get_agent_service),
) -> SubmitResponse:
    try:
        return service.submit_decisions(body.run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ErrorMessages.RUN_NOT_FOUND.format(run_id=body.run_id),
        )
    except RunAlreadySubmittedError:
        raise HTTPException(
            status_code=HTTPStatus.CONFLICT,
            detail=ErrorMessages.RUN_ALREADY_SUBMITTED,
        )
    except Exception:
        logger.exception("submit_decisions() failed")
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=ErrorMessages.SUBMIT_FAILED,
        )


@router.get(
    "/runs/{run_id}",
    response_model=RunResponse,
    status_code=HTTPStatus.OK,
    summary="Get decisions for a specific run",
    description="Retrieve all decisions recorded for a previous process run by its ID.",
    responses={
        **OpenAPIResponses.UNAUTHORIZED,
        **OpenAPIResponses.NOT_FOUND,
    },
)
def get_run(
    run_id: str,
    service: AgentServiceProtocol = Depends(get_agent_service),
) -> RunResponse:
    try:
        return service.get_run(run_id)
    except RunNotFoundError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=ErrorMessages.RUN_NOT_FOUND.format(run_id=run_id),
        )
