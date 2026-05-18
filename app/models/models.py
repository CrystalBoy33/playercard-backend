from sqlalchemy import (
    Column, String, Integer, Float, Text,
    DateTime, Boolean, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime, timezone

Base = declarative_base()


def utcnow():
    return datetime.now(timezone.utc)


class Player(Base):
    __tablename__ = "players"

    player_key   = Column(String(120), primary_key=True)  # "Name-Realm"
    name         = Column(String(60),  nullable=False)
    realm        = Column(String(60),  nullable=False)
    player_class = Column(String(30))
    spec         = Column(String(30))
    guild        = Column(String(60))
    item_level   = Column(Integer)
    avg_rating   = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    reviews      = relationship("Review",      back_populates="player", cascade="all, delete-orphan")
    endorsements = relationship("Endorsement", back_populates="player", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("player_key", "author", name="uq_player_author"),
    )

    id           = Column(Integer, primary_key=True, autoincrement=True)
    player_key   = Column(String(120), ForeignKey("players.player_key", ondelete="CASCADE"), nullable=False)
    author       = Column(String(60),  nullable=False)
    rating       = Column(Integer,     nullable=False)   # 1-5
    role         = Column(String(10),  default="UNKNOWN") # TANK / HEALER / DPS
    text         = Column(Text,        nullable=False)
    reply        = Column(Text)
    edited       = Column(Boolean,     default=False)
    report_count = Column(Integer,     default=0)
    created_at   = Column(DateTime(timezone=True), default=utcnow)
    updated_at   = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    player = relationship("Player", back_populates="reviews")


class Endorsement(Base):
    __tablename__ = "endorsements"
    __table_args__ = (
        UniqueConstraint("player_key", "author", "badge", name="uq_player_author_badge"),
    )

    id         = Column(Integer, primary_key=True, autoincrement=True)
    player_key = Column(String(120), ForeignKey("players.player_key", ondelete="CASCADE"), nullable=False)
    author     = Column(String(60), nullable=False)
    badge      = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    player = relationship("Player", back_populates="endorsements")


class KeystoneRun(Base):
    __tablename__ = "keystone_runs"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    player_key = Column(String(120), nullable=False, index=True)
    partner    = Column(String(120), nullable=False)   # the other player
    map_id     = Column(Integer, default=0)
    level      = Column(Integer, default=0)
    ran_at     = Column(DateTime(timezone=True), default=utcnow)
