from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import (
    Customer,
    Interaction,
    MaintenanceContract,
    Project,
    RevenueRecord,
    ServiceRecord,
)
from services.concentration import concentration_analysis, concentration_trend
from services.scoring import refresh_all_scores

router = APIRouter()


@router.get("/summary")
def dashboard_summary(db: Session = Depends(get_db)):
    """Top-level KPIs."""
    total_revenue = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0)).scalar()
    )
    current_year = datetime.now().year
    ytd_revenue = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0))
        .filter(RevenueRecord.fiscal_year == current_year)
        .scalar()
    )
    active_customers = (
        db.query(func.count(Customer.id))
        .filter(Customer.status == "active")
        .scalar()
    )
    active_projects = (
        db.query(func.count(Project.id))
        .filter(Project.stage.in_(["won", "in_progress"]))
        .scalar()
    )
    pipeline_value = (
        db.query(func.coalesce(func.sum(Project.bid_amount), 0))
        .filter(Project.stage.in_(["lead", "qualified", "estimating", "bid_submitted", "negotiation"]))
        .scalar()
    )
    active_contracts = (
        db.query(func.count(MaintenanceContract.id))
        .filter(MaintenanceContract.status == "active")
        .scalar()
    )
    contract_arr = (
        db.query(func.coalesce(func.sum(MaintenanceContract.annual_value), 0))
        .filter(MaintenanceContract.status == "active")
        .scalar()
    )
    open_service = (
        db.query(func.count(ServiceRecord.id))
        .filter(ServiceRecord.status.in_(["open", "scheduled", "in_progress"]))
        .scalar()
    )

    return {
        "total_revenue": total_revenue,
        "ytd_revenue": ytd_revenue,
        "active_customers": active_customers,
        "active_projects": active_projects,
        "pipeline_value": pipeline_value,
        "active_contracts": active_contracts,
        "contract_arr": contract_arr,
        "open_service_tickets": open_service,
    }


@router.get("/concentration")
def dashboard_concentration(
    fiscal_year: Optional[int] = None,
    db: Session = Depends(get_db),
):
    return concentration_analysis(db, fiscal_year)


@router.get("/concentration-trend")
def dashboard_concentration_trend(db: Session = Depends(get_db)):
    return concentration_trend(db)


@router.get("/pipeline-value")
def pipeline_value(db: Session = Depends(get_db)):
    """Weighted pipeline value by stage."""
    stage_weights = {
        "lead": 0.05,
        "qualified": 0.15,
        "estimating": 0.25,
        "bid_submitted": 0.40,
        "negotiation": 0.65,
        "won": 1.0,
    }
    result = {}
    for stage, weight in stage_weights.items():
        total = (
            db.query(func.coalesce(func.sum(Project.bid_amount), 0))
            .filter(Project.stage == stage)
            .scalar()
        )
        result[stage] = {
            "raw_value": total,
            "weighted_value": round(total * weight, 2),
            "weight": weight,
            "count": db.query(func.count(Project.id)).filter(Project.stage == stage).scalar(),
        }
    result["total_weighted"] = sum(s["weighted_value"] for s in result.values())
    return result


@router.get("/revenue-trend")
def revenue_trend(db: Session = Depends(get_db)):
    rows = (
        db.query(
            RevenueRecord.fiscal_year,
            RevenueRecord.fiscal_quarter,
            func.sum(RevenueRecord.amount).label("revenue"),
            func.sum(RevenueRecord.cost).label("cost"),
        )
        .group_by(RevenueRecord.fiscal_year, RevenueRecord.fiscal_quarter)
        .order_by(RevenueRecord.fiscal_year, RevenueRecord.fiscal_quarter)
        .all()
    )
    return [
        {
            "fiscal_year": r.fiscal_year,
            "fiscal_quarter": r.fiscal_quarter,
            "revenue": r.revenue,
            "cost": r.cost or 0,
            "margin": round((r.revenue - (r.cost or 0)) / r.revenue * 100, 1) if r.revenue else 0,
        }
        for r in rows
    ]


@router.get("/relationship-health")
def relationship_health(db: Session = Depends(get_db)):
    """Refresh scores and return sorted list."""
    results = refresh_all_scores(db)
    results.sort(key=lambda x: x["score"])
    return {
        "customers": results,
        "at_risk": [r for r in results if r["tier"] == "bronze"],
        "platinum_count": sum(1 for r in results if r["tier"] == "platinum"),
        "gold_count": sum(1 for r in results if r["tier"] == "gold"),
        "silver_count": sum(1 for r in results if r["tier"] == "silver"),
        "bronze_count": sum(1 for r in results if r["tier"] == "bronze"),
    }


@router.get("/win-rate")
def win_rate_analytics(db: Session = Depends(get_db)):
    """Win rate breakdown by project type and customer type."""
    # By project type
    by_type = {}
    types = db.query(Project.project_type).distinct().all()
    for (pt,) in types:
        won = db.query(func.count(Project.id)).filter(Project.stage == "won", Project.project_type == pt).scalar()
        lost = db.query(func.count(Project.id)).filter(Project.stage == "lost", Project.project_type == pt).scalar()
        total = won + lost
        by_type[pt] = {
            "won": won,
            "lost": lost,
            "win_rate": round(won / total * 100, 1) if total > 0 else 0,
        }

    # Overall
    won_total = db.query(func.count(Project.id)).filter(Project.stage == "won").scalar()
    lost_total = db.query(func.count(Project.id)).filter(Project.stage == "lost").scalar()
    overall = won_total + lost_total

    return {
        "overall_win_rate": round(won_total / overall * 100, 1) if overall > 0 else 0,
        "by_project_type": by_type,
    }


@router.get("/service-metrics")
def service_metrics(db: Session = Depends(get_db)):
    total = db.query(func.count(ServiceRecord.id)).scalar()
    completed = (
        db.query(func.count(ServiceRecord.id))
        .filter(ServiceRecord.status.in_(["completed", "invoiced"]))
        .scalar()
    )
    avg_satisfaction = (
        db.query(func.avg(ServiceRecord.customer_satisfaction))
        .filter(ServiceRecord.customer_satisfaction.isnot(None))
        .scalar()
    )
    total_service_revenue = (
        db.query(func.coalesce(func.sum(ServiceRecord.total_invoice), 0))
        .filter(ServiceRecord.status.in_(["completed", "invoiced"]))
        .scalar()
    )
    warranty_count = (
        db.query(func.count(ServiceRecord.id))
        .filter(ServiceRecord.is_warranty == 1)
        .scalar()
    )

    return {
        "total_records": total,
        "completed": completed,
        "avg_satisfaction": round(avg_satisfaction, 1) if avg_satisfaction else None,
        "total_service_revenue": total_service_revenue,
        "warranty_count": warranty_count,
    }
