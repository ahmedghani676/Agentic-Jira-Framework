"""Tool definitions handed to Claude for the bridge agent loop."""

TOOLS: list[dict] = [
    {
        "name": "get_teams_messages",
        "description": (
            "Fetch recent messages from the Microsoft Teams #feature-requests channel. "
            "Returns a list of messages with id, sender name, and text content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of messages to fetch (default 50).",
                    "default": 50,
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_jira_backlog",
        "description": (
            "Fetch all existing Jira tickets from the backlog. "
            "Use this to check whether a feature request already has an open ticket."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "search_hubspot_company",
        "description": (
            "Look up a company in HubSpot CRM by name to retrieve its "
            "Annual Recurring Revenue (ARR). Returns the ARR as an integer (USD) "
            "or null if the company is not found."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "Company name to search for (partial matches are fine).",
                }
            },
            "required": ["company_name"],
        },
    },
    {
        "name": "create_jira_ticket",
        "description": (
            "Create a new Jira Story ticket. Use this when no existing ticket "
            "matches the feature request."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The 'id' field of the Teams message this request came from.",
                },
                "client_name": {
                    "type": "string",
                    "description": "Name of the client company making the request.",
                },
                "arr": {
                    "type": "integer",
                    "description": "Client ARR in USD from HubSpot, or null if not found.",
                },
                "summary": {
                    "type": "string",
                    "description": "Short, clear ticket title (max ~80 chars).",
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Full ticket body. Must include: what was requested, "
                        "who requested it, the client name, and their ARR."
                    ),
                },
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional labels, e.g. ['feature-request', 'enterprise'].",
                },
            },
            "required": ["message_id", "client_name", "summary", "description"],
        },
    },
    {
        "name": "add_jira_comment",
        "description": (
            "Add a comment to an existing Jira ticket. Use this when a feature request "
            "matches an existing ticket — add context about the new requester and client."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The 'id' field of the Teams message this request came from.",
                },
                "client_name": {
                    "type": "string",
                    "description": "Name of the client company making the request.",
                },
                "arr": {
                    "type": "integer",
                    "description": "Client ARR in USD from HubSpot, or null if not found.",
                },
                "issue_key": {
                    "type": "string",
                    "description": "Jira issue key, e.g. JIRA-1042.",
                },
                "comment": {
                    "type": "string",
                    "description": (
                        "Comment text. Must mention: requester name, client name, "
                        "ARR, and any additional context from the message."
                    ),
                },
            },
            "required": ["message_id", "client_name", "issue_key", "comment"],
        },
    },
    {
        "name": "send_teams_feedback",
        "description": (
            "Send a confirmation message back to the Teams #feature-requests channel. "
            "Call this after every ticket action (create or update). "
            "Examples: 'Got it! Created new Ticket #JIRA-1200 for Hooli Inc. ($520k ARR).' "
            "or 'Got it! Added this to Ticket #JIRA-1042 for Hooli Inc. ($520k ARR).'"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "The 'id' field of the Teams message this confirmation is for.",
                },
                "message": {
                    "type": "string",
                    "description": "Confirmation message to post in Teams.",
                },
            },
            "required": ["message_id", "message"],
        },
    },
]
