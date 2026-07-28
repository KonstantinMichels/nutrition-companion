from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.modules.profiles.models import (
    ActivityProfile,
    DietaryRestriction,
    HealthScreening,
    NutritionGoal,
    Profile,
)


def get_profile(session: Session, profile_id: UUID) -> Profile | None:
    statement = (
        select(Profile)
        .where(Profile.id == profile_id)
        .options(
            selectinload(Profile.measurements),
            selectinload(Profile.activity_profile).selectinload(ActivityProfile.sports),
            selectinload(Profile.goal),
            selectinload(Profile.restrictions),
            selectinload(Profile.health_screening),
        )
    )
    return session.scalar(statement)


def get_activity(session: Session, profile_id: UUID) -> ActivityProfile | None:
    return session.scalar(
        select(ActivityProfile)
        .where(ActivityProfile.profile_id == profile_id)
        .options(selectinload(ActivityProfile.sports))
    )


def get_goal(session: Session, profile_id: UUID) -> NutritionGoal | None:
    return session.get(NutritionGoal, profile_id)


def get_restrictions(session: Session, profile_id: UUID) -> list[DietaryRestriction]:
    return list(
        session.scalars(
            select(DietaryRestriction)
            .where(DietaryRestriction.profile_id == profile_id)
            .order_by(DietaryRestriction.restriction_type, DietaryRestriction.value)
        )
    )


def get_health_screening(session: Session, profile_id: UUID) -> HealthScreening | None:
    return session.get(HealthScreening, profile_id)
