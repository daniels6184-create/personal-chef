"""Tables. The schema itself is created by Alembic migrations (backend/migrations), never by
create_all, so production and tests run the same DDL."""
import datetime as dt
import uuid
from decimal import Decimal

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer,
                        LargeBinary, Numeric, String, Text, func)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


# ------------------------------------------------------------------ auth

class AppSession(Base):
    __tablename__ = "app_session"
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256 of the cookie
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    method: Mapped[str] = mapped_column(String(16))  # password | passkey
    device: Mapped[str] = mapped_column(String(120), default="")


class LoginAttempt(Base):
    __tablename__ = "login_attempt"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip: Mapped[str] = mapped_column(String(64))
    success: Mapped[bool] = mapped_column(Boolean)


class PasskeyCredential(Base):
    __tablename__ = "passkey_credential"
    credential_id: Mapped[str] = mapped_column(String(512), primary_key=True)  # base64url
    public_key: Mapped[bytes] = mapped_column(LargeBinary)
    sign_count: Mapped[int] = mapped_column(Integer, default=0)
    transports: Mapped[list] = mapped_column(JSONB, default=list)
    name: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebauthnChallenge(Base):
    __tablename__ = "webauthn_challenge"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    challenge: Mapped[bytes] = mapped_column(LargeBinary)
    purpose: Mapped[str] = mapped_column(String(16))  # register | login
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))


# ------------------------------------------------------------------ profile

class Profile(Base):
    """Exactly one row (id = 1). Preferences are validated by app.schemas.Preferences before
    they are written, so the JSONB column never holds an unchecked shape."""
    __tablename__ = "profile"
    __table_args__ = (CheckConstraint("id = 1", name="profile_singleton"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80))
    birth_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[str | None] = mapped_column(String(16), nullable=True)
    height_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    preferences: Mapped[dict] = mapped_column(JSONB)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(),
                                                    onupdate=func.now())


class BodyMeasurement(Base):
    __tablename__ = "body_measurement"
    __table_args__ = (
        CheckConstraint("weight_kg IS NULL OR (weight_kg > 30 AND weight_kg < 250)", name="weight_range"),
        CheckConstraint("body_fat_pct IS NULL OR (body_fat_pct > 2 AND body_fat_pct < 60)", name="bf_range"),
        CheckConstraint("waist_cm IS NULL OR (waist_cm > 40 AND waist_cm < 200)", name="waist_range"),
        CheckConstraint("status IN ('verified','stated','estimated')", name="measurement_status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    measured_on: Mapped[dt.date] = mapped_column(Date, index=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(4, 1), nullable=True)
    waist_cm: Mapped[Decimal | None] = mapped_column(Numeric(5, 1), nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TargetVersion(Base):
    """Every nutrition target ever set. Exactly one row can be 'active' (partial unique index).
    The only way to make a row active is the approve endpoint; nothing edits an active row."""
    __tablename__ = "target_version"
    __table_args__ = (
        CheckConstraint("status IN ('active','proposed','rejected','superseded')", name="target_status"),
        CheckConstraint("origin IN ('stated','calculated','manual')", name="target_origin"),
        CheckConstraint("phase IN ('muscle_gain','fat_loss_maintain_muscle','maintenance')", name="target_phase"),
        CheckConstraint("kcal BETWEEN 1200 AND 6000", name="kcal_range"),
        CheckConstraint("protein_g BETWEEN 50 AND 400", name="protein_range"),
        CheckConstraint("carbs_g BETWEEN 0 AND 1000", name="carbs_range"),
        CheckConstraint("fat_g BETWEEN 20 AND 300", name="fat_range"),
    )
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    phase: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), index=True)
    origin: Mapped[str] = mapped_column(String(16))
    kcal: Mapped[int] = mapped_column(Integer)
    protein_g: Mapped[int] = mapped_column(Integer)
    carbs_g: Mapped[int] = mapped_column(Integer)
    fat_g: Mapped[int] = mapped_column(Integer)
    fibre_g: Mapped[int | None] = mapped_column(Integer, nullable=True)
    day_types: Mapped[dict] = mapped_column(JSONB, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    effective_from: Mapped[dt.date] = mapped_column(Date)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    decided_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("target_version.id"),
                                                            nullable=True)
