"""
Configuration centralisee via Pydantic Settings.
Charge automatiquement depuis les variables d'environnement.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Configuration de l'application."""

    # Domain (pour CORS et configuration)
    domain: Optional[str] = Field(
        default=None,
        description="Domaine principal (ex: dashboard.example.com)"
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

    # Documentation interactive (/docs, /redoc, /openapi.json) : coupee par defaut,
    # DOCS_ENABLED=true en developpement seulement.
    docs_enabled: bool = Field(default=False)

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

    # Session Sync : jeton du poste qui depose la session d'un tracker a connexion manuelle.
    # Accepte sur POST /scrapers/session/{tracker} seulement ; vide = jeton desactive.
    session_sync_token: Optional[str] = Field(
        default=None,
        min_length=32,
        description="Jeton dedie au depot de session (openssl rand -hex 32)"
    )

    # Cle de depot : en-tete X-Depot-Cle du script utilisateur (outils/trackboard-c411.user.js).
    # Acceptee sur POST /scrapers/session/{tracker} seulement ; vide = mode desactive.
    session_depot_cle: Optional[str] = Field(
        default=None,
        min_length=32,
        description="Cle dediee au depot de session par en-tete X-Depot-Cle (openssl rand -hex 32)"
    )

    @field_validator("session_sync_token", "session_depot_cle", mode="before")
    @classmethod
    def _jeton_vide(cls, v):
        # Le compose transmet une chaine vide quand la variable n'est pas definie.
        return v.strip() or None if isinstance(v, str) else v

    # Session manuelle : l'alerte Discord part quand il reste moins de ce nombre d'heures
    # avant l'expiration prevue (le renouvellement automatique aurait deja du avoir lieu).
    session_alerte_heures: float = Field(default=24, gt=0)

    @field_validator("session_alerte_heures", mode="before")
    @classmethod
    def _seuil_vide(cls, v):
        return 24 if isinstance(v, str) and not v.strip() else v

    # Notifications
    discord_webhook_url: Optional[str] = Field(
        default=None,
        description="URL du webhook Discord pour les alertes"
    )
    trackboard_url: Optional[str] = Field(
        default=None,
        description="URL de l'interface TrackBoard, pour les liens des alertes (facultatif)"
    )

    # Scraper
    scrape_interval: int = Field(
        default=3600,
        description="Intervalle entre les scrapes automatiques (secondes)"
    )

    # Media Services
    media_plex_url: Optional[str] = Field(default=None, description="URL Plex (ex: http://192.168.1.x:32400)")
    media_plex_token: Optional[str] = Field(default=None, description="Token Plex")
    media_radarr_url: Optional[str] = Field(default=None, description="URL Radarr (ex: http://192.168.1.x:7878)")
    media_radarr_api_key: Optional[str] = Field(default=None, description="Clé API Radarr")
    media_sonarr_url: Optional[str] = Field(default=None, description="URL Sonarr (ex: http://192.168.1.x:8989)")
    media_sonarr_api_key: Optional[str] = Field(default=None, description="Clé API Sonarr")
    media_tautulli_url: Optional[str] = Field(default=None, description="URL Tautulli (ex: http://192.168.1.x:8181)")
    media_tautulli_api_key: Optional[str] = Field(default=None, description="Clé API Tautulli")

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

    # Tracker Credentials - Ygg (yggreborn.org) et C411 : captcha a la connexion,
    # le scraper lit les cookies d une session ouverte a la main (capture_cookies.py)
    ygg_user: Optional[str] = None
    ygg_pass: Optional[str] = None
    ygg_username: Optional[str] = None
    c411_user: Optional[str] = None
    c411_pass: Optional[str] = None
    c411_username: Optional[str] = None

    # Tracker Credentials - Gemini
    gemini_user: Optional[str] = None
    gemini_pass: Optional[str] = None
    gemini_username: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Retourne l'instance de configuration (cached)."""
    return Settings()
