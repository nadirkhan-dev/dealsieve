from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[str] = mapped_column(String(32), index=True)

    # Imported fields (from a SaaSquatch export or any CRM CSV)
    name: Mapped[str] = mapped_column(String(255))
    name_key: Mapped[str] = mapped_column(String(255), index=True)
    domain: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    state: Mapped[str | None] = mapped_column(String(60), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    employees: Mapped[int | None] = mapped_column(Integer, nullable=True)
    revenue_estimate: Mapped[str | None] = mapped_column(String(60), nullable=True)
    owner_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    # Enrichment output
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|enriched|failed
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    signals: Mapped[dict] = mapped_column(JSON, default=dict)
    email_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Scoring output (recomputed instantly when the ICP changes; no re-crawl)
    score: Mapped[int] = mapped_column(Integer, default=0, index=True)
    tier: Mapped[str] = mapped_column(String(1), default="D", index=True)
    confidence: Mapped[int] = mapped_column(Integer, default=0)
    breakdown: Mapped[list] = mapped_column(JSON, default=list)
    flags: Mapped[list] = mapped_column(JSON, default=list)

    # Workflow
    stage: Mapped[str] = mapped_column(String(20), default="new", index=True)  # new|shortlist|contacted|passed
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    brief: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PageCache(Base):
    """HTTP response cache so re-running enrichment does not re-hit websites."""

    __tablename__ = "page_cache"

    url: Mapped[str] = mapped_column(String(1024), primary_key=True)
    status_code: Mapped[int] = mapped_column(Integer)
    final_url: Mapped[str] = mapped_column(String(1024))
    html: Mapped[str] = mapped_column(Text)
    blocked: Mapped[int] = mapped_column(Integer, default=0)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    done: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="running")  # running|finished
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)
