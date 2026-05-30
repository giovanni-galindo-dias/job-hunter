from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean
from datetime import datetime, timezone
from database import Base


class KanbanJob(Base):
    __tablename__ = "kanban_jobs"

    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), unique=True, index=True)
    title = Column(String(512), nullable=False)
    company = Column(String(255))
    location = Column(String(255))
    url = Column(Text)
    description = Column(Text)
    source = Column(String(64))
    score = Column(Float, default=0.0)           # fit_score
    seniority_score = Column(Integer, default=0)
    seniority_label = Column(String(32), default="")
    matched_skills = Column(Text, default="")
    column = Column(String(64), default="apply")
    posted_at = Column(String(32))
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    notes = Column(Text, default="")
    # ── Rastreamento de conversão (veredicto do conselho) ──────────────────
    interview_scheduled = Column(Boolean, default=False)  # entrevista marcada?
    offer_received = Column(Boolean, default=False)       # oferta recebida?
    applied_at = Column(DateTime, nullable=True)          # data da candidatura
    is_br = Column(Boolean, default=False)                # vaga brasileira?


class CollectedJob(Base):
    """Cache de vagas coletadas das APIs."""
    __tablename__ = "collected_jobs"

    id = Column(String(64), primary_key=True)
    title = Column(String(512), nullable=False)
    company = Column(String(255), default="")
    location = Column(String(255), default="")
    url = Column(Text, default="")
    description = Column(Text, default="")
    source = Column(String(64), default="")
    posted_at = Column(String(32), default="")
    is_br = Column(Boolean, default=False)
    is_new = Column(Boolean, default=False)
    fit_score = Column(Float, default=0.0)
    matched_skills = Column(Text, default="[]")
    role_type = Column(String(32), default="")
    seniority_score = Column(Integer, default=0)
    seniority_label = Column(String(32), default="")
    level_signals = Column(Text, default="[]")
    collected_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
