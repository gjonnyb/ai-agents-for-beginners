"""Deterministic relationship scoring engine.

Computes a 0–100 score for each customer based on recency, frequency,
revenue activity, contact depth, and satisfaction.  No LLM required.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import (
    Customer,
    Contact,
    Interaction,
    MaintenanceContract,
    Project,
    RevenueRecord,
    ServiceRecord,
)


def score_customer(customer_id: int, db: Session) -> dict:
    """Return {"score": float, "tier": str, "breakdown": dict}."""
    now = datetime.now(timezone.utc)
    breakdown: dict[str, float] = {}

    # ---- Recency (max 30) ----
    latest = (
        db.query(func.max(Interaction.interaction_date))
        .filter(Interaction.customer_id == customer_id)
        .scalar()
    )
    if latest:
        try:
            last_dt = datetime.fromisoformat(latest.replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
            days = (now - last_dt).days
        except Exception:
            days = 999
    else:
        days = 999

    if days <= 7:
        breakdown["recency"] = 30
    elif days <= 14:
        breakdown["recency"] = 25
    elif days <= 30:
        breakdown["recency"] = 20
    elif days <= 60:
        breakdown["recency"] = 10
    elif days <= 90:
        breakdown["recency"] = 5
    else:
        breakdown["recency"] = 0

    # ---- Frequency (max 20) ----
    ninety_ago = (now - timedelta(days=90)).isoformat()
    interaction_count = (
        db.query(func.count(Interaction.id))
        .filter(
            Interaction.customer_id == customer_id,
            Interaction.interaction_date >= ninety_ago,
        )
        .scalar()
    ) or 0

    if interaction_count >= 10:
        breakdown["frequency"] = 20
    elif interaction_count >= 6:
        breakdown["frequency"] = 15
    elif interaction_count >= 3:
        breakdown["frequency"] = 10
    elif interaction_count >= 1:
        breakdown["frequency"] = 5
    else:
        breakdown["frequency"] = 0

    # ---- Revenue / Activity (max 20) ----
    active_projects = (
        db.query(func.count(Project.id))
        .filter(
            Project.customer_id == customer_id,
            Project.stage.in_(["won", "in_progress", "negotiation"]),
        )
        .scalar()
    ) or 0

    if active_projects >= 3:
        breakdown["active_projects"] = 10
    elif active_projects >= 1:
        breakdown["active_projects"] = 7
    else:
        breakdown["active_projects"] = 0

    has_contract = (
        db.query(func.count(MaintenanceContract.id))
        .filter(
            MaintenanceContract.customer_id == customer_id,
            MaintenanceContract.status == "active",
        )
        .scalar()
    ) or 0
    breakdown["maintenance_contract"] = 5 if has_contract else 0

    # Revenue trend (YoY)
    current_year = now.year
    rev_this = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0))
        .filter(RevenueRecord.customer_id == customer_id, RevenueRecord.fiscal_year == current_year)
        .scalar()
    )
    rev_last = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0))
        .filter(RevenueRecord.customer_id == customer_id, RevenueRecord.fiscal_year == current_year - 1)
        .scalar()
    )
    if rev_this > rev_last and rev_last > 0:
        breakdown["revenue_trend"] = 5
    elif rev_this >= rev_last * 0.9:
        breakdown["revenue_trend"] = 3
    else:
        breakdown["revenue_trend"] = 0

    # ---- Depth (max 15) ----
    thirty_ago = (now - timedelta(days=90)).isoformat()
    contacts_with_interactions = (
        db.query(func.count(func.distinct(Interaction.contact_id)))
        .filter(
            Interaction.customer_id == customer_id,
            Interaction.contact_id.isnot(None),
            Interaction.interaction_date >= thirty_ago,
        )
        .scalar()
    ) or 0

    if contacts_with_interactions >= 3:
        breakdown["contact_breadth"] = 10
    elif contacts_with_interactions >= 2:
        breakdown["contact_breadth"] = 7
    elif contacts_with_interactions >= 1:
        breakdown["contact_breadth"] = 4
    else:
        breakdown["contact_breadth"] = 0

    has_dm = (
        db.query(func.count(Contact.id))
        .filter(Contact.customer_id == customer_id, Contact.role_type == "decision_maker")
        .scalar()
    ) or 0
    breakdown["decision_maker"] = 5 if has_dm else 0

    # ---- Satisfaction (max 15) ----
    twelve_ago = (now - timedelta(days=365)).isoformat()
    avg_sat = (
        db.query(func.avg(ServiceRecord.customer_satisfaction))
        .filter(
            ServiceRecord.customer_id == customer_id,
            ServiceRecord.customer_satisfaction.isnot(None),
            ServiceRecord.created_at >= twelve_ago,
        )
        .scalar()
    )
    if avg_sat is not None:
        if avg_sat >= 4.5:
            breakdown["satisfaction"] = 15
        elif avg_sat >= 3.5:
            breakdown["satisfaction"] = 12
        elif avg_sat >= 2.5:
            breakdown["satisfaction"] = 8
        elif avg_sat >= 1.5:
            breakdown["satisfaction"] = 3
        else:
            breakdown["satisfaction"] = 0
    else:
        breakdown["satisfaction"] = 5  # neutral if no data

    # Complaints penalty
    complaints = (
        db.query(func.count(Interaction.id))
        .filter(
            Interaction.customer_id == customer_id,
            Interaction.interaction_type == "complaint",
            Interaction.interaction_date >= twelve_ago,
        )
        .scalar()
    ) or 0
    if complaints > 0:
        breakdown["satisfaction"] = max(0, breakdown["satisfaction"] - 3 * complaints)

    score = sum(breakdown.values())
    score = max(0, min(100, score))

    if score >= 80:
        tier = "platinum"
    elif score >= 60:
        tier = "gold"
    elif score >= 40:
        tier = "silver"
    else:
        tier = "bronze"

    return {"score": round(score, 1), "tier": tier, "breakdown": breakdown}


def refresh_all_scores(db: Session) -> list[dict]:
    """Recompute and persist scores for all active customers."""
    customers = db.query(Customer).filter(Customer.status == "active").all()
    results = []
    for c in customers:
        result = score_customer(c.id, db)
        c.relationship_score = result["score"]
        c.relationship_tier = result["tier"]
        results.append({"customer_id": c.id, "name": c.name, **result})
    db.commit()
    return results
