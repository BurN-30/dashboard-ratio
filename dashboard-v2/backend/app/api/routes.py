"""
Routes API principales pour les donnees du dashboard.
Fournit les stats des trackers et l'historique.
"""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.auth.jwt import get_current_user, TokenData
from app.db.database import get_db
from app.db.models import TrackerStats

router = APIRouter()


@router.get("/stats")
async def get_latest_stats(
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne les dernieres statistiques de chaque tracker.

    Format compatible avec l'ancien frontend:
    {
        "Tracker1": { ratio, buffer, ... },
        "Tracker2": { ratio, buffer, ... },
        "_timestamp": 1234567890
    }
    """
    # Sous-requete pour obtenir le dernier ID de chaque tracker
    subquery = (
        select(
            TrackerStats.tracker_name,
            func.max(TrackerStats.id).label("max_id")
        )
        .group_by(TrackerStats.tracker_name)
        .subquery()
    )

    # Requete principale
    query = (
        select(TrackerStats)
        .join(
            subquery,
            (TrackerStats.tracker_name == subquery.c.tracker_name) &
            (TrackerStats.id == subquery.c.max_id)
        )
    )

    result = await db.execute(query)
    stats_list = result.scalars().all()

    # Formatter comme l'ancien format JSON
    response = {}
    latest_timestamp = None

    for stat in stats_list:
        response[stat.tracker_name] = {
            "ratio": str(stat.ratio) if stat.ratio else "0",
            "buffer": stat.buffer or "0",
            "vol_upload": stat.vol_upload or "0",
            "vol_download": stat.vol_download or "0",
            "points_bonus": stat.points_bonus or "0",
            "fl_tokens": stat.fl_tokens or "0",
            "count_seed": stat.count_seed or "0",
            "count_leech": stat.count_leech or "0",
            "count_downloaded": stat.count_downloaded or "0",
            "seed_time_total": stat.seed_time_total or "0",
            "seed_time_avg": stat.seed_time_avg or "0",
            "warnings_active": stat.warnings_active or "0",
            "hit_and_run": stat.hit_and_run or "0",
        }

        # Garder le timestamp le plus recent
        if stat.scraped_at:
            ts = int(stat.scraped_at.timestamp())
            if latest_timestamp is None or ts > latest_timestamp:
                latest_timestamp = ts

    response["_timestamp"] = latest_timestamp or int(datetime.now(timezone.utc).timestamp())

    return response


@router.get("/history")
async def get_stats_history(
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365, description="Nombre de jours d'historique"),
    tracker: Optional[str] = Query(default=None, description="Filtrer par tracker"),
):
    """
    Retourne l'historique des statistiques.

    Format compatible avec l'ancien frontend (tableau de snapshots).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(TrackerStats)
        .where(TrackerStats.scraped_at >= cutoff)
        .order_by(TrackerStats.scraped_at.asc())
    )

    if tracker:
        query = query.where(TrackerStats.tracker_name == tracker)

    result = await db.execute(query)
    stats_list = result.scalars().all()

    # Regrouper par timestamp (snapshot)
    snapshots = {}

    for stat in stats_list:
        ts = int(stat.scraped_at.timestamp())

        # Regrouper par fenetre de 5 minutes pour eviter les doublons
        ts_key = ts - (ts % 300)

        if ts_key not in snapshots:
            snapshots[ts_key] = {"_timestamp": ts_key}

        snapshots[ts_key][stat.tracker_name] = {
            "ratio": str(stat.ratio) if stat.ratio else "0",
            "buffer": stat.buffer or "0",
            "vol_upload": stat.vol_upload or "0",
            "vol_download": stat.vol_download or "0",
            "points_bonus": stat.points_bonus or "0",
            "count_seed": stat.count_seed or "0",
            "seed_time_total": stat.seed_time_total or "0",
            "seed_time_avg": stat.seed_time_avg or "0",
        }

    # Convertir en liste triee
    history = list(snapshots.values())
    history.sort(key=lambda x: x["_timestamp"])

    return history


@router.get("/stats/{tracker_name}")
async def get_tracker_stats(
    tracker_name: str,
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=1000),
):
    """
    Retourne l'historique detaille d'un tracker specifique.
    """
    query = (
        select(TrackerStats)
        .where(TrackerStats.tracker_name == tracker_name)
        .order_by(TrackerStats.scraped_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    stats_list = result.scalars().all()

    return {
        "tracker": tracker_name,
        "count": len(stats_list),
        "data": [stat.to_dict() for stat in stats_list],
    }


@router.get("/summary")
async def get_dashboard_summary(
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retourne un resume du dashboard.
    """
    # Compter les trackers avec des donnees
    count_query = select(func.count(func.distinct(TrackerStats.tracker_name)))
    result = await db.execute(count_query)
    tracker_count = result.scalar() or 0

    # Derniere mise a jour
    last_update_query = select(func.max(TrackerStats.scraped_at))
    result = await db.execute(last_update_query)
    last_update = result.scalar()

    # Stats totales
    total_query = select(func.count(TrackerStats.id))
    result = await db.execute(total_query)
    total_records = result.scalar() or 0

    return {
        "trackers_count": tracker_count,
        "total_records": total_records,
        "last_update": last_update.isoformat() if last_update else None,
    }
