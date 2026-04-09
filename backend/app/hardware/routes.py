"""
Routes pour le monitoring hardware.
Inclut les endpoints WebSocket, REST et historique.
"""
import logging
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.hardware.manager import hardware_manager
from app.auth.jwt import get_current_user, verify_token, TokenData
from app.db.database import get_db
from app.db.models import HardwareSnapshot

logger = logging.getLogger("dashboard.hardware")
router = APIRouter()


@router.websocket("/ws/agent")
async def hardware_agent_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Token d'authentification de l'agent"),
):
    """
    WebSocket pour l'agent hardware (PC local).

    L'agent envoie periodiquement les stats hardware.
    Authentification par token dans query string.
    """
    if not await hardware_manager.connect_agent(websocket, token):
        await websocket.close(code=4001, reason="Token invalide")
        return

    try:
        while True:
            # Recevoir les donnees de l'agent
            data = await websocket.receive_json()
            await hardware_manager.receive_data(data)

    except WebSocketDisconnect:
        await hardware_manager.disconnect_agent()
    except Exception as e:
        logger.error("Erreur agent WS: %s", e)
        await hardware_manager.disconnect_agent()


@router.websocket("/ws/client")
async def hardware_client_websocket(
    websocket: WebSocket,
    token: str = Query(..., description="Token JWT d'authentification"),
):
    """
    WebSocket pour les clients web (dashboard).

    Les clients recoivent les stats hardware en temps reel.
    Authentification par token JWT dans query string.
    """
    try:
        verify_token(token)
    except Exception:
        await websocket.close(code=4001, reason="Token invalide")
        return

    client_id = str(uuid.uuid4())
    await hardware_manager.connect_client(websocket, client_id)

    try:
        while True:
            # Garder la connexion ouverte (ping/pong gere par le protocole)
            # On peut aussi recevoir des commandes du client si necessaire
            message = await websocket.receive_text()

            if message == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        await hardware_manager.disconnect_client(client_id)
    except Exception as e:
        logger.error("Erreur client WS: %s", e)
        await hardware_manager.disconnect_client(client_id)


@router.get("/stats")
async def get_hardware_stats(user: TokenData = Depends(get_current_user)):
    """
    Endpoint REST pour obtenir les dernieres stats hardware.
    Alternative au WebSocket pour les requetes ponctuelles.
    """
    return hardware_manager.get_latest()


@router.get("/status")
async def get_hardware_status():
    """Retourne le status de connexion de l'agent hardware."""
    return {
        "agent_connected": hardware_manager.is_agent_connected,
        "clients_count": len(hardware_manager.clients),
    }


@router.get("/history")
async def get_hardware_history(
    hours: int = Query(default=24, ge=1, le=720, description="Nombre d'heures d'historique (max 30j)"),
    limit: int = Query(default=1000, ge=1, le=5000, description="Nombre max de snapshots"),
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Historique hardware depuis la DB.
    Retourne les snapshots dans l'ordre chronologique (plus ancien en premier).
    ASC order uses the recorded_at index directly.
    """
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    query = (
        select(HardwareSnapshot)
        .where(HardwareSnapshot.recorded_at >= since)
        .order_by(HardwareSnapshot.recorded_at.asc())
        .limit(limit)
    )
    result = await db.execute(query)
    snapshots = result.scalars().all()
    return [s.to_dict() for s in snapshots]


@router.get("/history/summary")
async def get_hardware_history_summary(
    user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compte de snapshots et plage temporelle disponible."""
    count = (await db.execute(select(func.count(HardwareSnapshot.id)))).scalar() or 0
    oldest = (await db.execute(select(func.min(HardwareSnapshot.recorded_at)))).scalar()
    newest = (await db.execute(select(func.max(HardwareSnapshot.recorded_at)))).scalar()
    return {
        "total_snapshots": count,
        "oldest_at": oldest.isoformat() if oldest else None,
        "newest_at": newest.isoformat() if newest else None,
    }
