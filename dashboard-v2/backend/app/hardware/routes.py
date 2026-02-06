"""
Routes pour le monitoring hardware.
Inclut les endpoints WebSocket et REST.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from typing import Optional
import uuid

from app.hardware.manager import hardware_manager
from app.auth.jwt import get_current_user, TokenData

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
async def hardware_client_websocket(websocket: WebSocket):
    """
    WebSocket pour les clients web (dashboard).

    Les clients recoivent les stats hardware en temps reel.
    Note: L'auth est geree cote frontend (cookie/token).
    """
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
