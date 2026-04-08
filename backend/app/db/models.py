"""
Modeles SQLAlchemy pour la base de donnees.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Index
from app.db.database import Base


class TrackerStats(Base):
    """Statistiques d'un tracker torrent."""

    __tablename__ = "tracker_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tracker_name = Column(String(100), nullable=False, index=True)

    # Stats principales
    ratio = Column(Float, nullable=True)
    buffer = Column(String(50), nullable=True)
    vol_upload = Column(String(50), nullable=True)
    vol_download = Column(String(50), nullable=True)

    # Stats secondaires
    points_bonus = Column(String(50), nullable=True)
    fl_tokens = Column(String(50), nullable=True)
    count_seed = Column(String(20), nullable=True)
    count_leech = Column(String(20), nullable=True)
    count_downloaded = Column(String(20), nullable=True)
    seed_time_total = Column(String(100), nullable=True)
    seed_time_avg = Column(String(100), nullable=True)
    warnings_active = Column(String(20), nullable=True)
    hit_and_run = Column(String(20), nullable=True)

    # Donnees brutes JSON (pour les champs non mappes)
    raw_data = Column(JSON, nullable=True)

    # Timestamps
    scraped_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Index pour les requetes frequentes
    __table_args__ = (
        Index("ix_tracker_stats_name_date", "tracker_name", "scraped_at"),
    )

    def to_dict(self) -> dict:
        """Convertit le modele en dictionnaire."""
        return {
            "id": self.id,
            "tracker_name": self.tracker_name,
            "ratio": str(self.ratio) if self.ratio else "0",
            "buffer": self.buffer or "0",
            "vol_upload": self.vol_upload or "0",
            "vol_download": self.vol_download or "0",
            "points_bonus": self.points_bonus or "0",
            "fl_tokens": self.fl_tokens or "0",
            "count_seed": self.count_seed or "0",
            "count_leech": self.count_leech or "0",
            "count_downloaded": self.count_downloaded or "0",
            "seed_time_total": self.seed_time_total or "0",
            "seed_time_avg": self.seed_time_avg or "0",
            "warnings_active": self.warnings_active or "0",
            "hit_and_run": self.hit_and_run or "0",
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
        }


class HardwareSnapshot(Base):
    """Snapshot des statistiques hardware."""

    __tablename__ = "hardware_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # CPU
    cpu_usage = Column(Float, nullable=True)
    cpu_temp = Column(Float, nullable=True)
    cpu_name = Column(String(200), nullable=True)

    # RAM
    ram_used_percent = Column(Float, nullable=True)
    ram_used_gb = Column(Float, nullable=True)
    ram_total_gb = Column(Float, nullable=True)

    # GPU
    gpu_usage = Column(Float, nullable=True)
    gpu_temp = Column(Float, nullable=True)
    gpu_name = Column(String(200), nullable=True)
    gpu_vram_used = Column(Float, nullable=True)

    # Storage (JSON pour plusieurs disques)
    storage = Column(JSON, nullable=True)

    # Donnees brutes completes
    raw_data = Column(JSON, nullable=True)

    # Timestamp
    recorded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    def to_dict(self) -> dict:
        """Convertit le modele en dictionnaire."""
        return {
            "cpu": {
                "usage": self.cpu_usage,
                "temp": self.cpu_temp,
                "name": self.cpu_name,
            },
            "ram": {
                "used_percent": self.ram_used_percent,
                "used_gb": self.ram_used_gb,
                "total_gb": self.ram_total_gb,
            },
            "gpu": {
                "usage": self.gpu_usage,
                "temp": self.gpu_temp,
                "name": self.gpu_name,
                "vram_used": self.gpu_vram_used,
            },
            "storage": self.storage or [],
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
        }
