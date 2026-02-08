"""
Registre des scrapers disponibles.
Configuration centralisee de tous les trackers supportes.
"""
import logging
from typing import Dict, List, Optional, Type
from app.scrapers.base import BaseScraper, ScraperConfig
from app.scrapers.unit3d import Unit3DScraper
from app.scrapers.sharewood import SharewoodScraper
from app.scrapers.torr9 import Torr9Scraper
from app.config import get_settings

logger = logging.getLogger("dashboard.scraper")
settings = get_settings()


# Configuration des sites supportes
SITES_CONFIG: List[dict] = [
    {
        "name": "GF-FREE",
        "scraper_class": Unit3DScraper,
        "login_url": "https://generation-free.org/login",
        "profile_url_template": "https://generation-free.org/users/{username}",
        "env_prefix": "gf",
    },
    {
        "name": "TOS",
        "scraper_class": Unit3DScraper,
        "login_url": "https://theoldschool.cc/login",
        "profile_url_template": "https://theoldschool.cc/users/{username}",
        "env_prefix": "tos",
    },
    {
        "name": "Sharewood",
        "scraper_class": SharewoodScraper,
        "login_url": "https://sharewood.tv/login",
        "profile_url_template": "https://www.sharewood.tv/{username}",
        "env_prefix": "sw",
    },
    {
        "name": "Torr9",
        "scraper_class": Torr9Scraper,
        "login_url": "https://torr9.xyz/login",
        "profile_url_template": "https://torr9.xyz/stats",  # Pas de profil standard
        "env_prefix": "torr9",
    },
    {
        "name": "G3MINI TR4CK3R",
        "scraper_class": Unit3DScraper,
        "login_url": "https://gemini-tracker.org/login",
        "profile_url_template": "https://gemini-tracker.org/users/{username}",
        "env_prefix": "gemini",
    },
]


def get_credentials_from_env(prefix: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Recupere les identifiants depuis les variables d'environnement.

    Args:
        prefix: Prefixe des variables (ex: "gf" pour GF_USER, GF_PASS, GF_USERNAME)

    Returns:
        Tuple (user, password, profile_username)
    """
    user = getattr(settings, f"{prefix}_user", None)
    password = getattr(settings, f"{prefix}_pass", None)
    username = getattr(settings, f"{prefix}_username", None)
    return user, password, username


def build_scrapers() -> Dict[str, BaseScraper]:
    """
    Construit les instances de scrapers configurees.

    Returns:
        Dict avec le nom du tracker comme cle et l'instance scraper comme valeur
    """
    scrapers = {}

    for site in SITES_CONFIG:
        user, password, profile_username = get_credentials_from_env(site["env_prefix"])

        # Skip si pas d'identifiants
        if not user or not password:
            logger.debug("%s: identifiants manquants, skip", site['name'])
            continue

        # Certains trackers exigent une transformation du username (ex: lowercase)
        login_user = user
        override = site.get("login_username_override")
        if override:
            login_user = override(user)

        config = ScraperConfig(
            name=site["name"],
            login_url=site["login_url"],
            profile_url_template=site["profile_url_template"],
            username=login_user,
            password=password,
            profile_username=profile_username or login_user,
        )

        scraper_class: Type[BaseScraper] = site["scraper_class"]
        scrapers[site["name"]] = scraper_class(config)
        logger.info("%s: configure", site['name'])

    return scrapers


# Instance globale des scrapers (lazy loading)
_scrapers: Optional[Dict[str, BaseScraper]] = None


def get_scrapers() -> Dict[str, BaseScraper]:
    """Retourne les scrapers (lazy init)."""
    global _scrapers
    if _scrapers is None:
        _scrapers = build_scrapers()
    return _scrapers


def get_scraper(name: str) -> Optional[BaseScraper]:
    """Retourne un scraper par son nom."""
    return get_scrapers().get(name)


def list_available_scrapers() -> List[str]:
    """Liste les scrapers disponibles (avec identifiants configures)."""
    return list(get_scrapers().keys())


def list_all_sites() -> List[dict]:
    """Liste tous les sites supportes (meme sans identifiants)."""
    return [
        {
            "name": site["name"],
            "login_url": site["login_url"],
            "configured": get_scraper(site["name"]) is not None,
        }
        for site in SITES_CONFIG
    ]
