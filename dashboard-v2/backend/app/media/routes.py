"""
Media Services Router - Plex, Radarr, Sonarr, Tautulli.
Aggrege les donnees de tous les services media en un seul endpoint.
"""
import asyncio
import logging
from typing import Optional

import httpx
from fastapi import APIRouter, Depends

from app.auth.jwt import TokenData, get_current_user
from app.config import get_settings

logger = logging.getLogger("dashboard.media")
router = APIRouter()

TIMEOUT = httpx.Timeout(10.0)


async def _fetch_plex(client: httpx.AsyncClient, url: str, token: str) -> Optional[dict]:
    """Recupere les donnees Plex (bibliotheques + sessions actives)."""
    try:
        headers = {"X-Plex-Token": token, "Accept": "application/json"}

        # Libraries
        libs_resp = await client.get(f"{url}/library/sections", headers=headers, timeout=TIMEOUT)
        libs_resp.raise_for_status()
        libs_data = libs_resp.json()
        sections = libs_data.get("MediaContainer", {}).get("Directory", [])

        libraries = []
        for section in sections:
            section_id = section.get("key")
            section_type = section.get("type", "unknown")
            count_resp = await client.get(
                f"{url}/library/sections/{section_id}/all",
                headers={**headers},
                params={"X-Plex-Container-Start": 0, "X-Plex-Container-Size": 0},
                timeout=TIMEOUT,
            )
            count_resp.raise_for_status()
            total = count_resp.json().get("MediaContainer", {}).get("totalSize", 0)
            libraries.append({
                "title": section.get("title"),
                "type": section_type,
                "count": total,
            })

        # Sessions
        sessions_resp = await client.get(f"{url}/status/sessions", headers=headers, timeout=TIMEOUT)
        sessions_resp.raise_for_status()
        sessions_data = sessions_resp.json().get("MediaContainer", {})
        active_streams = sessions_data.get("size", 0)

        return {
            "libraries": libraries,
            "active_streams": active_streams,
        }
    except Exception as e:
        logger.warning(f"Plex error: {e}")
        return None


async def _fetch_radarr(client: httpx.AsyncClient, url: str, api_key: str) -> Optional[dict]:
    """Recupere les donnees Radarr (films, queue, espace disque)."""
    try:
        headers = {"X-Api-Key": api_key}

        movie_resp, queue_resp, disk_resp, calendar_resp = await asyncio.gather(
            client.get(f"{url}/api/v3/movie", headers=headers, timeout=TIMEOUT),
            client.get(f"{url}/api/v3/queue", headers=headers, params={"pageSize": 50}, timeout=TIMEOUT),
            client.get(f"{url}/api/v3/diskspace", headers=headers, timeout=TIMEOUT),
            client.get(f"{url}/api/v3/calendar", headers=headers, params={"unmonitored": "false"}, timeout=TIMEOUT),
        )

        movies = movie_resp.json() if movie_resp.status_code == 200 else []
        queue_data = queue_resp.json() if queue_resp.status_code == 200 else {}
        disks = disk_resp.json() if disk_resp.status_code == 200 else []
        calendar = calendar_resp.json() if calendar_resp.status_code == 200 else []

        total_movies = len(movies)
        monitored = sum(1 for m in movies if m.get("monitored"))
        queue_count = queue_data.get("totalRecords", 0)

        disk_info = []
        for d in disks:
            disk_info.append({
                "path": d.get("path"),
                "free_gb": round(d.get("freeSpace", 0) / (1024**3), 1),
                "total_gb": round(d.get("totalSpace", 0) / (1024**3), 1),
            })

        upcoming = [
            {"title": m.get("title"), "year": m.get("year"), "status": m.get("status")}
            for m in calendar[:10]
        ]

        return {
            "total_movies": total_movies,
            "monitored": monitored,
            "queue_count": queue_count,
            "disk_space": disk_info,
            "upcoming": upcoming,
        }
    except Exception as e:
        logger.warning(f"Radarr error: {e}")
        return None


async def _fetch_sonarr(client: httpx.AsyncClient, url: str, api_key: str) -> Optional[dict]:
    """Recupere les donnees Sonarr (series, episodes, queue)."""
    try:
        headers = {"X-Api-Key": api_key}

        series_resp, queue_resp, calendar_resp = await asyncio.gather(
            client.get(f"{url}/api/v3/series", headers=headers, timeout=TIMEOUT),
            client.get(f"{url}/api/v3/queue", headers=headers, params={"pageSize": 50}, timeout=TIMEOUT),
            client.get(f"{url}/api/v3/calendar", headers=headers, params={"unmonitored": "false"}, timeout=TIMEOUT),
        )

        series = series_resp.json() if series_resp.status_code == 200 else []
        queue_data = queue_resp.json() if queue_resp.status_code == 200 else {}
        calendar = calendar_resp.json() if calendar_resp.status_code == 200 else []

        total_series = len(series)
        monitored = sum(1 for s in series if s.get("monitored"))
        total_episodes = sum(s.get("statistics", {}).get("episodeFileCount", 0) for s in series)
        queue_count = queue_data.get("totalRecords", 0)

        upcoming = [
            {
                "series": e.get("series", {}).get("title", "") or e.get("seriesTitle", ""),
                "title": e.get("title", ""),
                "season": e.get("seasonNumber"),
                "episode": e.get("episodeNumber"),
                "air_date": e.get("airDate"),
            }
            for e in calendar[:10]
        ]

        return {
            "total_series": total_series,
            "monitored": monitored,
            "total_episodes": total_episodes,
            "queue_count": queue_count,
            "upcoming": upcoming,
        }
    except Exception as e:
        logger.warning(f"Sonarr error: {e}")
        return None


async def _fetch_tautulli(client: httpx.AsyncClient, url: str, api_key: str) -> Optional[dict]:
    """Recupere les donnees Tautulli (activite, stats)."""
    try:
        params_base = {"apikey": api_key}

        activity_resp, stats_resp = await asyncio.gather(
            client.get(f"{url}/api/v2", params={**params_base, "cmd": "get_activity"}, timeout=TIMEOUT),
            client.get(f"{url}/api/v2", params={**params_base, "cmd": "get_home_stats", "stats_count": 5}, timeout=TIMEOUT),
        )

        activity = {}
        if activity_resp.status_code == 200:
            activity = activity_resp.json().get("response", {}).get("data", {})

        stats = []
        if stats_resp.status_code == 200:
            stats = stats_resp.json().get("response", {}).get("data", [])

        stream_count = activity.get("stream_count", 0)
        total_bandwidth = activity.get("total_bandwidth", 0)
        sessions = []
        for s in activity.get("sessions", []):
            sessions.append({
                "user": s.get("friendly_name", ""),
                "title": s.get("full_title", ""),
                "state": s.get("state", ""),
                "progress": s.get("progress_percent", "0"),
                "quality": s.get("quality_profile", ""),
                "player": s.get("player", ""),
            })

        # Extract most watched
        most_watched = []
        for stat_group in stats:
            if stat_group.get("stat_id") == "top_movies":
                for item in stat_group.get("rows", [])[:5]:
                    most_watched.append({
                        "title": item.get("title", ""),
                        "total_plays": item.get("total_plays", 0),
                    })

        return {
            "stream_count": stream_count,
            "total_bandwidth_mbps": round(total_bandwidth / 1000, 1) if total_bandwidth else 0,
            "sessions": sessions,
            "most_watched": most_watched,
        }
    except Exception as e:
        logger.warning(f"Tautulli error: {e}")
        return None


async def _noop() -> None:
    return None


@router.get("/overview")
async def media_overview(user: TokenData = Depends(get_current_user)):
    """Retourne un apercu agrege de tous les services media."""
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        plex_task = (
            _fetch_plex(client, settings.media_plex_url, settings.media_plex_token)
            if settings.media_plex_url and settings.media_plex_token
            else _noop()
        )
        radarr_task = (
            _fetch_radarr(client, settings.media_radarr_url, settings.media_radarr_api_key)
            if settings.media_radarr_url and settings.media_radarr_api_key
            else _noop()
        )
        sonarr_task = (
            _fetch_sonarr(client, settings.media_sonarr_url, settings.media_sonarr_api_key)
            if settings.media_sonarr_url and settings.media_sonarr_api_key
            else _noop()
        )
        tautulli_task = (
            _fetch_tautulli(client, settings.media_tautulli_url, settings.media_tautulli_api_key)
            if settings.media_tautulli_url and settings.media_tautulli_api_key
            else _noop()
        )

        plex, radarr, sonarr, tautulli = await asyncio.gather(
            plex_task, radarr_task, sonarr_task, tautulli_task,
            return_exceptions=True,
        )

    def safe(r):
        return None if isinstance(r, BaseException) else r

    return {
        "plex": safe(plex),
        "radarr": safe(radarr),
        "sonarr": safe(sonarr),
        "tautulli": safe(tautulli),
    }
