"""
Notifications Discord via webhook.
Non-bloquant, ne crash jamais l'app.

Alertes actives :
- Scrape fail (3+ consecutifs) + recovery
- Ratio drop sous 1.0
- Agent hardware disconnect (>5min) + reconnect
"""
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger("dashboard.notifications")


def _get_webhook_url() -> str | None:
    settings = get_settings()
    url = getattr(settings, "discord_webhook_url", None)
    return url if url else None


async def _send(embed: dict):
    """Envoie un embed Discord. Fire-and-forget, ne crash jamais."""
    url = _get_webhook_url()
    if not url:
        return

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"username": "TrackBoard", "embeds": [embed]})
            if resp.status_code not in (200, 204):
                logger.warning("Discord webhook returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Failed to send Discord notification: %s", e)


async def notify_scrape_failures(tracker_name: str, consecutive: int, last_error: str | None):
    """Alerte quand un tracker echoue 3+ fois de suite."""
    if consecutive < 3:
        return
    await _send({
        "title": f"Scrape echoue : {tracker_name}",
        "description": f"**{consecutive}** echecs consecutifs.",
        "color": 0xFF4444,
        "fields": [{"name": "Erreur", "value": f"```{(last_error or 'unknown')[:200]}```", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_scrape_recovery(tracker_name: str, consecutive_before: int):
    """Quand un tracker se retablit apres 3+ echecs."""
    if consecutive_before < 3:
        return
    await _send({
        "title": f"Scrape retabli : {tracker_name}",
        "description": f"De retour apres **{consecutive_before}** echecs.",
        "color": 0x44BB44,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_ratio_drop(tracker_name: str, old_ratio: float, new_ratio: float):
    """Alerte quand un ratio passe sous 1.0."""
    if new_ratio >= 1.0 or old_ratio < 1.0:
        return
    await _send({
        "title": f"Ratio critique : {tracker_name}",
        "description": f"Ratio passe sous 1.0",
        "color": 0xFF8800,
        "fields": [
            {"name": "Avant", "value": str(old_ratio), "inline": True},
            {"name": "Maintenant", "value": f"**{new_ratio}**", "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_agent_disconnect():
    """Agent hardware offline depuis 5 min."""
    await _send({
        "title": "PC offline",
        "description": "L'agent hardware ne repond plus depuis 5 minutes.",
        "color": 0xFF8800,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_agent_reconnect():
    """Agent hardware de retour."""
    await _send({
        "title": "PC de retour",
        "description": "L'agent hardware est reconnecte.",
        "color": 0x44BB44,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
