"""Revenue concentration analysis.

Measures customer revenue concentration using per-customer share
and the Herfindahl-Hirschman Index (HHI).
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import get_settings
from db.models import Customer, RevenueRecord


def concentration_analysis(
    db: Session,
    fiscal_year: int | None = None,
) -> dict:
    """Return concentration metrics for a given fiscal year (or all-time)."""
    settings = get_settings()

    q = db.query(
        RevenueRecord.customer_id,
        func.sum(RevenueRecord.amount).label("total"),
    )
    if fiscal_year:
        q = q.filter(RevenueRecord.fiscal_year == fiscal_year)
    q = q.group_by(RevenueRecord.customer_id).order_by(func.sum(RevenueRecord.amount).desc())

    rows = q.all()
    if not rows:
        return {
            "total_revenue": 0,
            "customer_count": 0,
            "hhi": 0,
            "concentration_level": "N/A",
            "customers": [],
            "flags": [],
        }

    total_revenue = sum(r.total for r in rows)
    customers = []
    hhi = 0.0
    flags = []

    for r in rows:
        cust = db.query(Customer).filter(Customer.id == r.customer_id).first()
        share_pct = (r.total / total_revenue * 100) if total_revenue > 0 else 0
        hhi += share_pct ** 2
        entry = {
            "customer_id": r.customer_id,
            "customer_name": cust.name if cust else "Unknown",
            "revenue": r.total,
            "share_pct": round(share_pct, 1),
        }
        customers.append(entry)

        if share_pct > settings.concentration_single_customer_threshold:
            flags.append(
                f"{entry['customer_name']} represents {entry['share_pct']}% of revenue "
                f"(threshold: {settings.concentration_single_customer_threshold}%)"
            )

    # Top-3 check
    top3_share = sum(c["share_pct"] for c in customers[:3])
    if top3_share > settings.concentration_top3_threshold:
        names = ", ".join(c["customer_name"] for c in customers[:3])
        flags.append(
            f"Top 3 customers ({names}) represent {round(top3_share, 1)}% of revenue "
            f"(threshold: {settings.concentration_top3_threshold}%)"
        )

    hhi = round(hhi, 0)
    if hhi > 2500:
        level = "highly_concentrated"
    elif hhi > 1500:
        level = "moderately_concentrated"
    else:
        level = "diversified"

    return {
        "total_revenue": total_revenue,
        "customer_count": len(customers),
        "hhi": hhi,
        "concentration_level": level,
        "customers": customers,
        "flags": flags,
        "fiscal_year": fiscal_year,
    }


def concentration_trend(db: Session) -> list[dict]:
    """HHI and concentration level for each fiscal year with data."""
    years = (
        db.query(RevenueRecord.fiscal_year)
        .distinct()
        .order_by(RevenueRecord.fiscal_year)
        .all()
    )
    return [
        {
            "fiscal_year": y[0],
            "hhi": concentration_analysis(db, y[0])["hhi"],
            "level": concentration_analysis(db, y[0])["concentration_level"],
            "total_revenue": concentration_analysis(db, y[0])["total_revenue"],
        }
        for y in years
    ]
