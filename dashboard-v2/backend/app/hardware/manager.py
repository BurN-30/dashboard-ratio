"""
Gestionnaire de connexions hardware WebSocket.
Gere les connexions des agents hardware et la diffusion aux clients.
"""
import logging
from typing import Dict, Optional
from datetime import datetime
from dataclasses import dataclass, field
from fastapi import WebSocket
import json
import asyncio

logger = logging.getLogger("dashboard.hardware")


@dataclass
class HardwareData:
    """Donnees hardware recues de l'agent."""
    cpu: dict = field(default_factory=dict)
    ram: dict = field(default_factory=dict)
    gpu: dict = field(default_factory=dict)
    storage: list = field(default_factory=list)
    network: dict = field(default_factory=dict)
    processes: list = field(default_factory=list)
    os: str = ""
    uptime: str = ""
    hostname: str = ""
    timestamp: Optional[str] = None
    agent_connected: bool = False


class HardwareManager:
    """
    Gestionnaire central pour les donnees hardware.

    - Recoit les donnees de l'agent (PC local)
    - Diffuse aux clients web connectes
    - Maintient un cache des dernieres donnees
    """

    def __init__(self):
        self.agent_ws: Optional[WebSocket] = None
        self.agent_token: Optional[str] = None
        self.clients: Dict[str, WebSocket] = {}
        self.latest_data: HardwareData = HardwareData()
        self._lock = asyncio.Lock()

    async def connect_agent(self, websocket: WebSocket, token: str) -> bool:
        """Connecte l'agent hardware."""
        from app.config import get_settings
        settings = get_settings()

        if token != settings.hw_agent_token:
            return False

        async with self._lock:
            if self.agent_ws:
                try:
                    await self.agent_ws.close()
                except:
                    pass

            await websocket.accept()
            self.agent_ws = websocket
            self.agent_token = token
            self.latest_data.agent_connected = True

            logger.info("Agent connecte")
            return True

    async def disconnect_agent(self):
        """Deconnecte l'agent hardware."""
        async with self._lock:
            self.agent_ws = None
            self.agent_token = None
            self.latest_data.agent_connected = False
            logger.info("Agent deconnecte")

    async def connect_client(self, websocket: WebSocket, client_id: str):
        """Connecte un client web."""
        await websocket.accept()
        async with self._lock:
            self.clients[client_id] = websocket
            logger.debug("Client connecte: %s", client_id)

            if self.latest_data.timestamp:
                try:
                    await websocket.send_json(self._format_data())
                except:
                    pass

    async def disconnect_client(self, client_id: str):
        """Deconnecte un client web."""
        async with self._lock:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.debug("Client deconnecte: %s", client_id)

    async def receive_data(self, data: dict):
        """Recoit des donnees de l'agent et les diffuse aux clients."""
        async with self._lock:
            self.latest_data = HardwareData(
                cpu=data.get("cpu", {}),
                ram=data.get("ram", {}),
                gpu=data.get("gpu"),
                storage=data.get("storage", []),
                network=data.get("network", {}),
                processes=data.get("processes", []),
                os=data.get("os", ""),
                uptime=data.get("uptime", ""),
                hostname=data.get("hostname", ""),
                timestamp=data.get("timestamp", datetime.utcnow().isoformat()),
                agent_connected=True,
            )

        await self.broadcast()

    async def broadcast(self):
        """Diffuse les dernieres donnees a tous les clients."""
        if not self.clients:
            return

        data = self._format_data()
        disconnected = []

        for client_id, ws in self.clients.items():
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning("Erreur envoi client %s: %s", client_id, e)
                disconnected.append(client_id)

        for client_id in disconnected:
            await self.disconnect_client(client_id)

    def _format_data(self) -> dict:
        """Formate les donnees pour l'envoi."""
        return {
            "cpu": self.latest_data.cpu,
            "ram": self.latest_data.ram,
            "gpu": self.latest_data.gpu,
            "storage": self.latest_data.storage,
            "network": self.latest_data.network,
            "processes": self.latest_data.processes,
            "os": self.latest_data.os,
            "uptime": self.latest_data.uptime,
            "hostname": self.latest_data.hostname,
            "timestamp": self.latest_data.timestamp,
            "agent_connected": self.latest_data.agent_connected,
        }

    def get_latest(self) -> dict:
        """Retourne les dernieres donnees (pour API REST)."""
        return self._format_data()

    @property
    def is_agent_connected(self) -> bool:
        """Verifie si l'agent est connecte."""
        return self.agent_ws is not None


# Instance globale
hardware_manager = HardwareManager()
