from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.reference_data.models import ApplicationRuleSet, ReferenceSet


def current_reference_set(session: Session) -> ReferenceSet | None:
    return session.scalar(
        select(ReferenceSet)
        .where(ReferenceSet.effective_date <= date.today())
        .order_by(ReferenceSet.effective_date.desc(), ReferenceSet.created_at.desc())
        .limit(1)
    )


def current_application_rule_set(session: Session) -> ApplicationRuleSet | None:
    return session.scalar(
        select(ApplicationRuleSet)
        .where(ApplicationRuleSet.effective_date <= date.today())
        .order_by(ApplicationRuleSet.effective_date.desc(), ApplicationRuleSet.created_at.desc())
        .limit(1)
    )
