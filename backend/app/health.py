"""
Healthchecks reels de TrackBoard.

`/health` : public, minimal (statut global + version). Compatible Docker HEALTHCHECK.
`/health/full` : auth requise, detail composant par composant.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models import TrackerStats, HardwareSnapshot
from app.scrapers import registry
from app.scrapers import scheduler as scheduler_mod
from app.hardware.manager import hardware_manager
from app.auth.jwt import get_current_user, TokenData

logger = logging.getLogger("dashboard.health")
router = APIRouter()

VERSION = "2.0.0"


async def _check_database(db: AsyncSession) -> dict:
    """Ping DB + mesure latence."""
    start = datetime.now(timezone.utc)
    try:
        result = await db.execute(text("SELECT 1"))
        value = result.scalar()
        latency_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
        return {
            "status": "ok" if value == 1 else "degraded",
            "latency_ms": round(latency_ms, 1),
        }
    except Exception as e:
        return {"status": "down", "error": type(e).__name__, "detail": str(e)[:200]}


def _check_scheduler() -> dict:
    """Etat de la tache asyncio du scheduler de scraping."""
    task = scheduler_mod._scheduler_task
    if task is None:
        return {"status": "down", "running": False, "reason": "task_not_started"}
    if task.done():
        exc = None
        try:
            exc = task.exception()
        except Exception:
            pass
        return {
            "status": "down",
            "running": False,
            "reason": "task_finished",
            "exception": type(exc).__name__ if exc else None,
        }
    # Tache vivante : prochaine execution
    try:
        wait_seconds = scheduler_mod._seconds_until_next_run()
        next_run_at = (
            datetime.now(scheduler_mod.TZ) + timedelta(seconds=wait_seconds)
        ).isoformat()
    except Exception:
        next_run_at = None
    return {
        "status": "ok",
        "running": True,
        "next_run_at": next_run_at,
    }


def _check_hardware_agent() -> dict:
    """Etat de l'agent hardware (PC home)."""
    connected = hardware_manager.is_agent_connected
    last_ts = hardware_manager.latest_data.timestamp

    if not connected:
        return {
            "status": "down",
            "connected": False,
            "last_message_at": last_ts,
            "clients_count": len(hardware_manager.clients),
        }

    # Considere "stale" si pas de message depuis 30s
    stale = False
    if last_ts:
        try:
            last_dt = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            stale = (datetime.now(timezone.utc) - last_dt).total_seconds() > 30
        except Exception:
            pass

    return {
        "status": "degraded" if stale else "ok",
        "connected": True,
        "stale": stale,
        "last_message_at": last_ts,
        "clients_count": len(hardware_manager.clients),
    }


def _check_scrapers() -> dict:
    """Liste les scrapers configures (avec credentials valides)."""
    try:
        all_sites = registry.list_all_sites()
        configured = registry.list_available_scrapers()
        return {
            "status": "ok" if configured else "degraded",
            "configured_count": len(configured),
            "total_sites": len(all_sites),
            "configured": configured,
        }
    except Exception as e:
        return {"status": "down", "error": type(e).__name__, "detail": str(e)[:200]}


async def _check_last_scrapes(db: AsyncSession) -> dict:
    """Date du dernier scrape par tracker."""
    try:
        query = (
            select(
                TrackerStats.tracker_name,
                func.max(TrackerStats.scraped_at).label("last_at"),
            )
            .group_by(TrackerStats.tracker_name)
        )
        result = await db.execute(query)
        rows = result.all()
        return {
            row.tracker_name: row.last_at.isoformat() if row.last_at else None
            for row in rows
        }
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


async def _check_hardware_history(db: AsyncSession) -> dict:
    """Compte des snapshots hardware en DB + dernier."""
    try:
        count_q = select(func.count(HardwareSnapshot.id))
        last_q = select(func.max(HardwareSnapshot.recorded_at))
        count = (await db.execute(count_q)).scalar() or 0
        last = (await db.execute(last_q)).scalar()
        return {
            "snapshots_total": int(count),
            "last_snapshot_at": last.isoformat() if last else None,
        }
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {str(e)[:200]}"}


def _aggregate_status(checks: dict[str, dict]) -> str:
    """Synthese : ok / degraded / down."""
    statuses = [c.get("status", "unknown") for c in checks.values() if isinstance(c, dict)]
    if "down" in statuses:
        return "down"
    if "degraded" in statuses or "unknown" in statuses:
        return "degraded"
    return "ok"


# ==================================================================
# ENDPOINTS
# ==================================================================

@router.get("/health")
async def health_minimal(db: AsyncSession = Depends(get_db)):
    """
    Healthcheck public minimal.
    Compatible avec Docker HEALTHCHECK et monitoring externe.
    Retourne uniquement le statut global et la version, pas de details.
    """
    db_check = await _check_database(db)
    sched_check = _check_scheduler()
    agent_check = _check_hardware_agent()

    overall = _aggregate_status({
        "database": db_check,
        "scheduler": sched_check,
        "hardware_agent": agent_check,
    })

    # Pour le HEALTHCHECK Docker, on veut un 200 si la DB est OK
    # meme si le scheduler ou l'agent sont down (ils peuvent etre transitoirement KO).
    return {
        "status": overall,
        "version": VERSION,
    }


@router.get("/health/full")
async def health_full(
    db: AsyncSession = Depends(get_db),
    user: TokenData = Depends(get_current_user),
):
    """
    Healthcheck detaille (auth requise).
    Retourne l'etat de chaque composant + dernier scrape par tracker
    + nombre de snapshots hardware.
    """
    db_check = await _check_database(db)
    sched_check = _check_scheduler()
    agent_check = _check_hardware_agent()
    scrapers_check = _check_scrapers()
    last_scrapes = await _check_last_scrapes(db)
    hw_history = await _check_hardware_history(db)

    overall = _aggregate_status({
        "database": db_check,
        "scheduler": sched_check,
        "hardware_agent": agent_check,
        "scrapers": scrapers_check,
    })

    return {
        "status": overall,
        "version": VERSION,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "database": db_check,
            "scheduler": sched_check,
            "hardware_agent": agent_check,
            "scrapers": scrapers_check,
        },
        "last_scrapes_by_tracker": last_scrapes,
        "hardware_history": hw_history,
    }
