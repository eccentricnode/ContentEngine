"""Configuration management for Content Engine."""

import os
from typing import Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from lib.errors import ConfigurationError


# Load .env file
load_dotenv()


class LinkedInConfig(BaseSettings):
    """LinkedIn API configuration."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    client_id: str = Field(..., alias="LINKEDIN_CLIENT_ID")
    client_secret: str = Field(..., alias="LINKEDIN_CLIENT_SECRET")
    access_token: Optional[str] = Field(None, alias="LINKEDIN_ACCESS_TOKEN")
    user_sub: Optional[str] = Field(None, alias="LINKEDIN_USER_SUB")
    redirect_uri: str = Field(default="http://localhost:3000/callback", alias="REDIRECT_URI")


class ServerConfig(BaseSettings):
    """Server configuration."""

    model_config = SettingsConfigDict(env_file=".env")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=3000, alias="PORT")


def get_linkedin_config() -> LinkedInConfig:
    """Get LinkedIn configuration from environment."""
    try:
        return LinkedInConfig()
    except Exception as e:
        raise ConfigurationError(
            f"Failed to load LinkedIn configuration: {e}. "
            "Make sure .env file exists and contains required variables."
        )


def get_server_config() -> ServerConfig:
    """Get server configuration from environment."""
    try:
        return ServerConfig()
    except Exception as e:
        raise ConfigurationError(f"Failed to load server configuration: {e}")
