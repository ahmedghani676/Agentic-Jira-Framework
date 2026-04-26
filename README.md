<<<<<<< HEAD
# AI-Engineer-Coding-Challenge
=======
# WorkFlex Bridge Agent

An AI-native backend service that reads Microsoft Teams `#feature-requests` messages, cross-references HubSpot CRM for customer ARR, checks Jira for duplicate tickets, and proposes a set of actions for human review before writing anything to Jira or Teams.

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Docker Network                    │
│                                                     │
│  ┌──────────────────┐      ┌─────────────────────┐  │
│  │   bridge-agent   │      │      mock-api        │  │
│  │   :8000          │─────▶│      :8080           │  │
│  │                  │      │                      │  │
│  │  FastAPI + Claude│      │  Simulates:          │  │
│  │  Anthropic SDK   │      │  • Jira Cloud v3     │  │
│  └──────────────────┘      │  • HubSpot CRM v3    │  │
│                            │  • MS Graph (Teams)  │  │
│                            └─────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

Two services run via Docker Compose. The bridge-agent talks to the mock-api over the internal Docker network. All Jira, HubSpot, and Teams tokens are fetched automatically from the mock server at runtime — no manual token management required.

---

## How It Works

The agent uses a **two-phase human-in-the-loop design**:

### Phase 1 — `POST /api/process` (Dry Run)

1. Fetches up to 50 messages from the Teams `#feature-requests` channel
2. Loads the full Jira backlog
3. For each feature-request message, Claude:
   - Looks up the client company in HubSpot to get their ARR
   - Checks Jira for an existing ticket covering the same feature
   - Decides: **CREATE** a new ticket, **UPDATE** an existing one with a comment, or **SKIP** (non-feature messages)
4. Returns all proposed decisions with a `run_id` — **nothing is written yet**

### Phase 2 — `POST /api/submit` (Execute)

1. Takes the `run_id` from Phase 1
2. Executes all non-SKIP decisions: creates Jira tickets, adds comments, posts Teams confirmations
3. Can only be called once per `run_id` (duplicate-submission guard)

---

## Project Structure

```
AI Engineer Coding Challenge 1/
├── docker-compose.yml
├── README.md
├── bridge-agent/
│   ├── main.py                    # Entry point
│   ├── config.py                  # Pydantic settings (env vars)
│   ├── agent/
│   │   ├── bridge.py              # Agentic loop + ToolDispatcher
│   │   ├── tools.py               # Claude tool definitions
│   │   ├── prompts.py             # System prompt
│   │   └── exceptions.py          # AgentLoopError, AgentTimeoutError, AgentContextError
│   ├── clients/
│   │   ├── jira.py                # Jira REST API v3 client
│   │   ├── hubspot.py             # HubSpot CRM API v3 client
│   │   └── teams.py               # Microsoft Graph (Teams) client
│   ├── services/
│   │   ├── agent_service.py       # Business logic (process / submit / get_run)
│   │   ├── protocols.py           # AgentServiceProtocol (dependency inversion)
│   │   └── dependencies.py        # FastAPI Depends factory
│   ├── routes/
│   │   ├── agent.py               # POST /api/process, POST /api/submit, GET /api/runs/{id}
│   │   ├── health.py              # GET /health
│   │   └── ui.py                  # Admin UI static files
│   ├── models/
│   │   ├── agent_decision.py      # DecisionItem dataclass
│   │   ├── api_requests/          # Request models (SubmitRequest)
│   │   ├── api_responses/         # Response models (ProcessResponse, SubmitResponse, ...)
│   │   └── integrations/          # Jira, HubSpot, Teams typed models
│   ├── store/
│   │   └── session.py             # In-memory SessionStore (run_id -> decisions)
│   ├── core/
│   │   ├── app.py                 # FastAPI app factory + lifespan
│   │   ├── startup.py             # Config validation at startup
│   │   ├── middleware.py          # Middleware registration
│   │   ├── auth_middleware.py     # X-API-Key authentication
│   │   ├── request_logging.py     # Structured JSON request/response logging
│   │   └── logging_config.py      # JSON log formatter + request_id ContextVar
│   ├── constants/                 # HTTP status codes, error messages, OpenAPI tags
│   ├── tests/
│   │   ├── unit/                  # ToolDispatcher, AgentService, SessionStore tests
│   │   └── integration/           # Full route tests with dependency overrides
│   ├── Dockerfile                 # Multi-stage build
│   ├── requirements.txt
│   ├── .env.example               # Template — copy to .env and fill in secrets
│   └── .env                       # Real secrets — gitignored, never committed
└── mock-api/
    ├── mock_server.py             # FastAPI mock for Jira, HubSpot, Teams
    ├── jira_backlog.json          # Seed data — existing Jira tickets
    ├── crm_data.json              # Seed data — HubSpot companies + ARR
    ├── teams_messages.json        # Seed data — 70 Teams messages (60 feature requests + 10 noise)
    ├── requirements.txt
    └── Dockerfile
```

---

## API Endpoints

### Bridge Agent (`localhost:8000`)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/api/process` | Run Claude agent in dry-run mode — returns proposed decisions |
| `POST` | `/api/submit` | Execute approved decisions against Jira + Teams |
| `GET` | `/api/runs/{run_id}` | Retrieve decisions for a previous run |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/` | Admin UI |

### Mock API (`localhost:8080`)

| Service | Base Path |
|---------|-----------|
| Jira Cloud REST v3 | `/jira/rest/api/3/...` |
| HubSpot CRM v3 | `/hubspot/crm/v3/...` |
| Microsoft Graph (Teams) | `/graph/v1.0/...` |
| Token Dashboard | `/dashboard` |
| Swagger UI | `/docs` |

---

## Quick Start

### Prerequisites

- Docker Desktop
- An [Anthropic API key](https://console.anthropic.com)

### 1. Configure environment

```bash
cp bridge-agent/.env.example bridge-agent/.env
```

Then edit `bridge-agent/.env` and set your Anthropic API key:

```env
ANTHROPIC_API_KEY=sk-ant-...
```

All Jira, HubSpot, and Teams tokens are fetched automatically from the mock server at runtime — no dashboard steps or manual token copying required.

> **Never commit `.env`** — it contains your real API key. Only `.env.example` (with placeholders) is tracked in git.

### 2. Start the services

```bash
# Start mock API first
docker compose up -d mock-api

# Start the bridge agent
docker compose up -d bridge-agent
```

### 3. Use the Admin UI

Open `http://localhost:8000` in your browser to use the Admin Console.

Or call the API directly:

**Phase 1 — analyse messages and get proposed decisions:**

```bash
curl -X POST http://localhost:8000/api/process
```

Response:

```json
{
  "run_id": "8df06e2b-96ac-4beb-a799-a9d2dc797968",
  "total": 50,
  "decisions": [
    {
      "message_id": "1742203800000",
      "sender": "Lisa Brandt",
      "client_name": "Hooli",
      "arr": 520000,
      "action": "CREATE",
      "draft_summary": "SSO via SAML for Enterprise Clients"
    }
  ]
}
```

**Phase 2 — execute the approved decisions:**

```bash
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"run_id": "8df06e2b-96ac-4beb-a799-a9d2dc797968"}'
```

**Retrieve a previous run:**

```bash
curl http://localhost:8000/api/runs/8df06e2b-96ac-4beb-a799-a9d2dc797968
```

---

## Configuration

All settings are in `bridge-agent/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | *(required)* | Your Anthropic API key |
| `CLAUDE_MODEL` | `claude-sonnet-4-6` | Claude model to use |
| `MOCK_BASE_URL` | `http://localhost:8080` | Mock API base URL (overridden to `http://mock-api:8080` inside Docker) |
| `JIRA_EMAIL` | `candidate@workflex.com` | Email for Jira Basic auth username |
| `TEAMS_CLIENT_ID` | `bridge-agent` | Client ID for Teams OAuth2 flow |
| `TEAMS_MESSAGE_LIMIT` | `50` | Max Teams messages to fetch per run |
| `AGENT_MAX_ITERATIONS` | `50` | Max Claude loop iterations (hallucination guard) |
| `AGENT_TIMEOUT_SECONDS` | `120.0` | Anthropic API call timeout in seconds |
| `API_KEY` | *(empty)* | X-API-Key for endpoint auth — leave empty to disable in dev |

---

## Token Management

Tokens are managed automatically. The bridge agent fetches them from the mock server on first use and caches them in process memory:

| Service | Flow |
|---------|------|
| **Jira** | `POST /auth/tokens/jira` → Basic auth token cached in-process |
| **HubSpot** | `POST /auth/tokens/hubspot` → Bearer token cached in-process |
| **Teams** | `POST /auth/tokens/teams` → client secret → `POST /auth/teams/token` → Bearer token cached with expiry |

If the mock server restarts and invalidates tokens, each client automatically detects the 401, fetches a fresh token, and retries the original request transparently.

---

## Running Tests

```bash
cd bridge-agent
pip install -r requirements.txt
pytest tests/ -v
```

Test coverage includes:

- **Unit** — `ToolDispatcher` tool routing and decision tracking, `AgentService` process/submit/get_run logic, `SessionStore` CRUD and duplicate-submission guard
- **Integration** — All API routes with mocked service layer, auth middleware enforcement, correct HTTP status codes for all error cases

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI + Uvicorn |
| AI agent | Anthropic Claude (`claude-sonnet-4-6`) via tool use |
| HTTP clients | httpx (shared connection pools per service) |
| Config | pydantic-settings |
| Data validation | Pydantic v2 |
| Logging | Structured JSON with `request_id` threaded through all log lines |
| Authentication | X-API-Key middleware |
| Containers | Docker multi-stage build + Docker Compose |
| Tests | pytest |

---

## Design Decisions

**Two-phase process/submit** — Claude proposes decisions in dry-run mode; a human reviews before anything is written to Jira or Teams. Prevents hallucinated or incorrect tickets from being created automatically.

**Per-message decision tracking** — Each action tool (`create_jira_ticket`, `add_jira_comment`, `send_teams_feedback`) carries an explicit `message_id` so decisions are correctly associated with their source Teams message even when Claude batches multiple tool calls in a single response turn.

**Automatic token refresh** — All three API clients fetch tokens from the mock server on first use and retry with a fresh token on any 401. No manual token rotation or dashboard interaction needed after startup.

**Dependency inversion** — Controllers depend on `AgentServiceProtocol` (a structural `Protocol` class), not the concrete `AgentService`. Routes are fully testable via FastAPI `dependency_overrides` without touching production code.

**Connection pooling** — Each client (`jira`, `hubspot`, `teams`) holds a module-level `httpx.Client` that reuses TCP connections across all requests for that service.

**Context window guard** — The agent loop is capped at `AGENT_MAX_ITERATIONS` turns and raises `AgentContextError` if the Anthropic API reports the context window has been exceeded, preventing runaway costs.
>>>>>>> AICodingChallenge-1
