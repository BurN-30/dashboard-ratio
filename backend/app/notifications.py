"""
Notifications Discord via webhook.
Non-bloquant, ne crash jamais l'app.

Alertes :
- Scrape fail (3+ consecutifs) + recovery
- Ratio sous 0.85 (@here)
- Hit & Run nouveau + critique 2+ (@here)
- Agent hardware offline >1h (@here) + reconnect
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


async def _send(embed: dict, ping_here: bool = False):
    """Envoie un embed Discord. Fire-and-forget, ne crash jamais."""
    url = _get_webhook_url()
    if not url:
        return

    try:
        payload = {"username": "TrackBoard", "embeds": [embed]}
        if ping_here:
            payload["content"] = "@here"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code not in (200, 204):
                logger.warning("Discord webhook %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Discord notification failed: %s", e)


# === SCRAPE ===

async def notify_scrape_failures(tracker_name: str, consecutive: int, last_error: str | None):
    """3+ echecs consecutifs."""
    if consecutive < 3:
        return
    await _send({
        "title": f"Scrape echoue : {tracker_name}",
        "description": f"**{consecutive}** echecs consecutifs.",
        "color": 0xFF4444,
        "fields": [{"name": "Erreur", "value": f"```{(last_error or '?')[:200]}```", "inline": False}],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_scrape_recovery(tracker_name: str, consecutive_before: int):
    """Recovery apres 3+ echecs."""
    if consecutive_before < 3:
        return
    await _send({
        "title": f"Scrape retabli : {tracker_name}",
        "description": f"De retour apres **{consecutive_before}** echecs.",
        "color": 0x44BB44,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


# === RATIO ===

async def notify_ratio_critical(tracker_name: str, ratio: float):
    """Ratio passe sous 0.85. @here."""
    await _send({
        "title": f"Ratio critique : {tracker_name}",
        "description": f"Ratio a **{ratio:.2f}** (seuil : 0.85)",
        "color": 0xFF4444,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ping_here=True)


# === HIT & RUN ===

async def notify_hit_and_run(tracker_name: str, count: int):
    """Nouveau H&R detecte."""
    await _send({
        "title": f"Hit & Run : {tracker_name}",
        "description": f"**{count}** H&R actif(s) detecte(s).",
        "color": 0xFF8800,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def notify_hit_and_run_critical(tracker_name: str, count: int):
    """2+ H&R actifs. @here."""
    await _send({
        "title": f"H&R critique : {tracker_name}",
        "description": f"**{count}** Hit & Run actifs — risque de ban.",
        "color": 0xFF4444,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ping_here=True)


# === HARDWARE AGENT ===

async def notify_agent_disconnect():
    """PC offline depuis 1h. @here."""
    await _send({
        "title": "PC offline",
        "description": "L'agent hardware ne repond plus depuis 1 heure.",
        "color": 0xFF8800,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, ping_here=True)


async def notify_agent_reconnect():
    """PC de retour."""
    await _send({
        "title": "PC de retour",
        "description": "L'agent hardware est reconnecte.",
        "color": 0x44BB44,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
