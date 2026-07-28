from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, utc_now

if TYPE_CHECKING:
    from app.modules.nutrition_assessment.models import Assessment
    from app.modules.privacy.models import ConsentRecord


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    physiological_category: Mapped[str] = mapped_column(String(32), nullable=False)
    height_cm: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    current_weight_kg: Mapped[Decimal] = mapped_column(Numeric(7, 3), nullable=False)
    dietary_preference: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_meals_per_day: Mapped[int | None] = mapped_column(Integer)
    preferred_meal_timing: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    measurements: Mapped[list[Measurement]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    activity_profile: Mapped[ActivityProfile | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    goal: Mapped[NutritionGoal | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    restrictions: Mapped[list[DietaryRestriction]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    health_screening: Mapped[HealthScreening | None] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    assessments: Mapped[list[Assessment]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )
    consent_records: Mapped[list[ConsentRecord]] = relationship(
        back_populates="profile", cascade="all, delete-orphan", passive_deletes=True
    )


class Measurement(Base):
    __tablename__ = "measurements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    measurement_type: Mapped[str] = mapped_column(String(48), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    unit: Mapped[str] = mapped_column(String(24), nullable=False)
    measured_at: Mapped[date] = mapped_column(Date, nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped[Profile] = relationship(back_populates="measurements")


class ActivityProfile(Base):
    __tablename__ = "activity_profiles"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    occupational_activity_category: Mapped[str] = mapped_column(String(64), nullable=False)
    average_daily_steps: Mapped[int | None] = mapped_column(Integer)
    active_commuting: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    movement_notes: Mapped[str | None] = mapped_column(String(500))
    manual_pal_override: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    profile: Mapped[Profile] = relationship(back_populates="activity_profile")
    sports: Mapped[list[SportActivity]] = relationship(
        back_populates="activity_profile", cascade="all, delete-orphan", passive_deletes=True
    )


class SportActivity(Base):
    __tablename__ = "sport_activities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    activity_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("activity_profiles.profile_id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport_type: Mapped[str] = mapped_column(String(64), nullable=False)
    sessions_per_week: Mapped[Decimal] = mapped_column(Numeric(4, 2), nullable=False)
    minutes_per_session: Mapped[int] = mapped_column(Integer, nullable=False)
    intensity: Mapped[str] = mapped_column(String(24), nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))

    activity_profile: Mapped[ActivityProfile] = relationship(back_populates="sports")


class NutritionGoal(Base):
    __tablename__ = "nutrition_goals"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    goal_type: Mapped[str] = mapped_column(String(48), nullable=False)
    target_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    desired_intensity: Mapped[str | None] = mapped_column(String(24))
    requested_weekly_rate_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 3))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    profile: Mapped[Profile] = relationship(back_populates="goal")


class DietaryRestriction(Base):
    __tablename__ = "dietary_restrictions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    restriction_type: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(String(200), nullable=False)
    hard_exclusion: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500))

    profile: Mapped[Profile] = relationship(back_populates="restrictions")


class HealthScreening(Base):
    __tablename__ = "health_screenings"

    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True
    )
    pregnant: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    breastfeeding: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    diagnosed_eating_disorder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    diabetes: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    kidney_disease: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    liver_disease: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    medically_prescribed_diet: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    serious_metabolic_condition: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    other_professional_nutrition_condition: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    user_note: Mapped[str | None] = mapped_column(Text)
    screened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    profile: Mapped[Profile] = relationship(back_populates="health_screening")
