from collections.abc import Generator

from sqlalchemy import Column, DateTime, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.sql import func

from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TimestampMixin:
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injector for FastAPI.
    Yields a scoped database session and closes it after the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
