"""Backward-compatible Celery application import."""

from app.infrastructure.celery import celery

__all__ = ["celery"]
