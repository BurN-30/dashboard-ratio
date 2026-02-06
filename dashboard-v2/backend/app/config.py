"""
Configuration centralisee via Pydantic Settings.
Charge automatiquement depuis les variables d'environnement.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application."""

    # Domain (pour CORS et configuration)
    domain: Optional[str] = Field(
        default=None,
        description="Domaine principal (ex: example.com)"
    )
    cors_origins: Optional[list[str]] = Field(
        default=None,
        description="Origines CORS supplementaires (liste)"
    )

    # Database
    database_url: str = Field(
        default="sqlite:///./dashboard.db",
        description="URL de connexion a la base de donnees"
    )

    # JWT Auth
    jwt_secret: str = Field(
        default="change-me-in-production",
        min_length=32,
        description="Cle secrete pour signer les JWT"
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expire_hours: int = Field(default=24)

    # Admin
    admin_password: str = Field(
        default="admin",
        description="Mot de passe administrateur"
    )

    # Hardware Agent
    hw_agent_token: str = Field(
        default="change-me",
        description="Token pour authentifier l'agent hardware"
    )

    # Scraper
    scrape_interval: int = Field(
        default=3600,
        description="Intervalle entre les scrapes automatiques (secondes)"
    )

    # Tracker Credentials - Sharewood
    sw_user: Optional[str] = None
    sw_pass: Optional[str] = None
    sw_username: Optional[str] = None

    # Tracker Credentials - Generation-Free
    gf_user: Optional[str] = None
    gf_pass: Optional[str] = None
    gf_username: Optional[str] = None

    # Tracker Credentials - TheOldSchool
    tos_user: Optional[str] = None
    tos_pass: Optional[str] = None
    tos_username: Optional[str] = None

    # Tracker Credentials - Torr9
    torr9_user: Optional[str] = None
    torr9_pass: Optional[str] = None
    torr9_username: Optional[str] = None

    # Tracker Credentials - Gemini
    gemini_user: Optional[str] = None
    gemini_pass: Optional[str] = None
    gemini_username: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance de configuration (cached)."""
    return Settings()
