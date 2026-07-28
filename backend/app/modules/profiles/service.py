from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.database.base import utc_now
from app.modules.profiles import repository
from app.modules.profiles.models import (
    ActivityProfile,
    DietaryRestriction,
    HealthScreening,
    Measurement,
    NutritionGoal,
    Profile,
    SportActivity,
)
from app.modules.profiles.schemas import (
    ActivityUpdate,
    GoalUpdate,
    HealthScreeningUpdate,
    ProfileUpdate,
    RestrictionsUpdate,
)


def require_profile(session: Session, profile_id: UUID) -> Profile:
    profile = repository.get_profile(session, profile_id)
    if profile is None:
        raise ApiError(
            code="PROFILE_NOT_FOUND",
            message="Es wurde noch kein Profil gespeichert.",
            status_code=404,
        )
    return profile


def update_profile(session: Session, profile_id: UUID, payload: ProfileUpdate) -> Profile:
    profile = repository.get_profile(session, profile_id)
    values = payload.model_dump(exclude={"measurements"})
    if profile is None:
        profile = Profile(id=profile_id, **values)
        session.add(profile)
    else:
        for key, value in values.items():
            setattr(profile, key, value)
        profile.measurements.clear()

    profile.measurements.extend(
        Measurement(profile_id=profile_id, **measurement.model_dump())
        for measurement in payload.measurements
    )
    session.commit()
    return require_profile(session, profile_id)


def update_activity(session: Session, profile_id: UUID, payload: ActivityUpdate) -> ActivityProfile:
    require_profile(session, profile_id)
    activity = repository.get_activity(session, profile_id)
    values = payload.model_dump(exclude={"sports"})
    if activity is None:
        activity = ActivityProfile(profile_id=profile_id, **values)
        session.add(activity)
    else:
        for key, value in values.items():
            setattr(activity, key, value)
        activity.sports.clear()
    activity.sports.extend(
        SportActivity(activity_profile_id=profile_id, **sport.model_dump())
        for sport in payload.sports
    )
    session.commit()
    refreshed = repository.get_activity(session, profile_id)
    assert refreshed is not None
    return refreshed


def update_goal(session: Session, profile_id: UUID, payload: GoalUpdate) -> NutritionGoal:
    require_profile(session, profile_id)
    goal = repository.get_goal(session, profile_id)
    values = payload.model_dump()
    if goal is None:
        goal = NutritionGoal(profile_id=profile_id, **values)
        session.add(goal)
    else:
        for key, value in values.items():
            setattr(goal, key, value)
    session.commit()
    return goal


def update_restrictions(
    session: Session, profile_id: UUID, payload: RestrictionsUpdate
) -> list[DietaryRestriction]:
    profile = require_profile(session, profile_id)
    profile.restrictions.clear()
    profile.restrictions.extend(
        DietaryRestriction(profile_id=profile_id, **restriction.model_dump())
        for restriction in payload.restrictions
    )
    session.commit()
    return repository.get_restrictions(session, profile_id)


def update_health_screening(
    session: Session, profile_id: UUID, payload: HealthScreeningUpdate
) -> HealthScreening:
    require_profile(session, profile_id)
    screening = repository.get_health_screening(session, profile_id)
    values = payload.model_dump()
    if screening is None:
        screening = HealthScreening(profile_id=profile_id, **values)
        session.add(screening)
    else:
        for key, value in values.items():
            setattr(screening, key, value)
        screening.screened_at = utc_now()
    session.commit()
    return screening
