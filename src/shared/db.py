import os
import uuid
import logging
from datetime import datetime
from typing import Iterator, Optional

from sqlalchemy import Boolean, DateTime, Integer, Text, String, JSON, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

logger = logging.getLogger(__name__)


def _get_database_url() -> str:
    return os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://ks_los:secure_password@localhost:5432/ks_los_db",
    )


class Base(DeclarativeBase):
    pass


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    borrower_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    chat_role: Mapped[str] = mapped_column(Text, nullable=False, default="borrower")
    current_phase_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    seriousness_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    fit_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    intent_summary: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommended_products: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    next_conversation_angle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_officer: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[dict]] = mapped_column("metadata", JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class LoanPhase(Base):
    __tablename__ = "loan_phases"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    color: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="#2dd4bf")
    icon: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="circle")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


_engine = None
_SessionLocal: Optional[sessionmaker[Session]] = None
_initialized = False


def _create_sqlite_fallback_engine():
    url = os.getenv("SQLITE_FALLBACK_URL", "sqlite:///./ks_los_v2.db")
    return create_engine(url, connect_args={"check_same_thread": False})


def get_engine():
    global _engine
    if _engine is not None:
        return _engine

    try:
        engine = create_engine(_get_database_url(), pool_pre_ping=True)
        with engine.connect() as _:
            pass
        _engine = engine
        return _engine
    except Exception as e:
        logger.warning(f"Database connection failed; using SQLite fallback. Error: {e}")
        _engine = _create_sqlite_fallback_engine()
        return _engine


def init_db():
    global _initialized, _SessionLocal
    if _initialized:
        return
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    _SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    _initialized = True


def get_db() -> Iterator[Session]:
    init_db()
    assert _SessionLocal is not None
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_db_for_tests():
    global _engine, _SessionLocal, _initialized
    _engine = None
    _SessionLocal = None
    _initialized = False
