"""Run Alembic migrations programmatically (used at startup and in tests)."""
import logging
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

log = logging.getLogger(__name__)
BACKEND_DIR = Path(__file__).resolve().parents[1]


def alembic_config(url: Optional[str] = None) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    if url:
        cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def upgrade_to_head(url: Optional[str] = None) -> None:
    """Upgrade to head. Databases created before migrations existed (tables present but no
    alembic_version) are stamped at the baseline first so nothing is recreated."""
    from .db import SQLALCHEMY_DATABASE_URL

    effective = url or SQLALCHEMY_DATABASE_URL
    cfg = alembic_config(effective)
    engine = create_engine(effective, connect_args={"check_same_thread": False} if effective.startswith("sqlite") else {})
    tables = set(inspect(engine).get_table_names())
    engine.dispose()
    if "alembic_version" not in tables and "discovery_runs" in tables:
        log.info("Legacy database detected - stamping baseline revision 0001")
        command.stamp(cfg, "0001")
    command.upgrade(cfg, "head")
    log.info("Database schema is at head")
