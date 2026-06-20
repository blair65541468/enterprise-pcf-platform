"""Backward-compatible database imports."""

from app.core.db import Base, SessionLocal, UnitOfWork, engine, get_db

__all__ = ["Base", "SessionLocal", "UnitOfWork", "engine", "get_db"]
