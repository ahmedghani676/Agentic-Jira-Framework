from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Anthropic
    anthropic_api_key: str
    claude_model: str = "claude-sonnet-4-6"

    # Mock server base URL
    mock_base_url: str = "http://localhost:8080"

    # Jira — email used as Basic-auth username; token is fetched from mock server at runtime
    jira_email: str = "candidate@workflex.com"

    # Microsoft Teams — client_id used in the OAuth2 flow; secret is fetched from mock server
    teams_client_id: str = "bridge-agent"

    # How many Teams messages to pull per run (max 50 per mock API page)
    teams_message_limit: int = 50

    # Agent loop safety limits
    agent_max_iterations: int = 50
    agent_timeout_seconds: float = 120.0

    # API authentication — set to a strong secret in production.
    # Leave empty to disable auth (development only).
    api_key: str = ""


settings = Settings()
