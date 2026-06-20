from collections.abc import Generator
from contextlib import AbstractContextManager
from types import TracebackType
from typing import Literal

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as db:
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    """Owns one SQLAlchemy transaction at an API or worker boundary."""

    def __init__(self, session: Session):
        self.session = session
        self._completed = False

    def __enter__(self) -> "UnitOfWork":
        return self

    def commit(self) -> None:
        self.session.commit()
        self._completed = True

    def rollback(self) -> None:
        self.session.rollback()
        self._completed = True

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        if exc_type is not None:
            self.session.rollback()
        elif not self._completed:
            self.session.commit()
        return False
