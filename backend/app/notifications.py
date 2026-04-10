"""
Notifications Discord via webhook.
Non-bloquant, rate-limited, ne crash jamais l'app.
"""
import logging
import time
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger("dashboard.notifications")

# Cooldown par cle de notification (evite le spam).
# Format: {"scrape_fail:Torr9": timestamp_dernier_envoi}
_cooldowns: dict[str, float] = {}
COOLDOWN_SECONDS = 3600  # 1 notification par type par heure max


def _should_send(key: str) -> bool:
    """Verifie si le cooldown est ecoule pour cette notification."""
    now = time.time()
    last = _cooldowns.get(key, 0)
    if now - last < COOLDOWN_SECONDS:
        return False
    _cooldowns[key] = now
    return True


def _get_webhook_url() -> str | None:
    """Retourne l'URL du webhook Discord, ou None si non configure."""
    settings = get_settings()
    url = getattr(settings, "discord_webhook_url", None)
    return url if url else None


async def _send(embed: dict, key: str):
    """Envoie un embed Discord si le cooldown est OK."""
    url = _get_webhook_url()
    if not url:
        return

    if not _should_send(key):
        logger.debug("Notification %s en cooldown, skip", key)
        return

    try:
        payload = {
            "username": "TrackBoard",
            "embeds": [embed],
        }
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code not in (200, 204):
                logger.warning("Discord webhook returned %s: %s", resp.status_code, resp.text[:200])
    except Exception as e:
        logger.warning("Failed to send Discord notification: %s", e)


# ============================================================
# Public notification functions
# ============================================================

async def notify_scrape_failures(tracker_name: str, consecutive: int, last_error: str | None):
    """Alerte quand un tracker echoue 3+ fois de suite."""
    if consecutive < 3:
        return

    await _send({
        "title": f"Scrape echoue: {tracker_name}",
        "description": f"**{consecutive}** echecs consecutifs.",
        "color": 0xFF4444,  # rouge
        "fields": [
            {"name": "Derniere erreur", "value": f"```{(last_error or 'unknown')[:200]}```", "inline": False},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key=f"scrape_fail:{tracker_name}")


async def notify_ratio_drop(tracker_name: str, old_ratio: float, new_ratio: float):
    """Alerte quand un ratio passe sous 1.0."""
    if new_ratio >= 1.0 or old_ratio < 1.0:
        return  # Pas de drop, ou etait deja sous 1

    await _send({
        "title": f"Ratio critique: {tracker_name}",
        "description": f"Le ratio est passe sous 1.0",
        "color": 0xFF8800,  # orange
        "fields": [
            {"name": "Ancien ratio", "value": str(old_ratio), "inline": True},
            {"name": "Nouveau ratio", "value": f"**{new_ratio}**", "inline": True},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key=f"ratio_drop:{tracker_name}")


async def notify_agent_disconnect():
    """Alerte quand l'agent hardware se deconnecte."""
    await _send({
        "title": "Agent hardware deconnecte",
        "description": "Le PC local ne repond plus depuis 5 minutes.",
        "color": 0xFF8800,  # orange
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key="agent_disconnect")


async def notify_agent_reconnect():
    """Info quand l'agent hardware se reconnecte."""
    await _send({
        "title": "Agent hardware reconnecte",
        "description": "Le PC local est de retour en ligne.",
        "color": 0x44BB44,  # vert
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key="agent_reconnect")


async def notify_disk_critical(drive_name: str, percent: float):
    """Alerte quand un disque depasse 90%."""
    if percent < 90:
        return

    await _send({
        "title": f"Disque critique: {drive_name}",
        "description": f"Utilisation a **{percent:.1f}%**",
        "color": 0xFF4444 if percent >= 95 else 0xFF8800,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key=f"disk_critical:{drive_name}")


async def notify_scrape_recovery(tracker_name: str, consecutive_before: int):
    """Info quand un tracker se retablit apres des echecs."""
    if consecutive_before < 3:
        return

    await _send({
        "title": f"Scrape retabli: {tracker_name}",
        "description": f"De retour apres **{consecutive_before}** echecs.",
        "color": 0x44BB44,  # vert
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }, key=f"scrape_recovery:{tracker_name}")
