from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Project, Customer, _utcnow

router = APIRouter()


class ProjectCreate(BaseModel):
    customer_id: int
    name: str
    project_type: str
    description: Optional[str] = None
    stage: str = "lead"
    priority: str = "medium"
    bid_amount: Optional[float] = None
    estimated_cost: Optional[float] = None
    contract_value: Optional[float] = None
    estimated_margin_pct: Optional[float] = None
    general_contractor: Optional[str] = None
    project_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    square_footage: Optional[int] = None
    bid_due_date: Optional[str] = None
    estimated_start_date: Optional[str] = None
    estimated_end_date: Optional[str] = None
    win_probability: float = 0.5
    assigned_estimator: Optional[str] = None
    assigned_pm: Optional[str] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    project_type: Optional[str] = None
    stage: Optional[str] = None
    priority: Optional[str] = None
    bid_amount: Optional[float] = None
    estimated_cost: Optional[float] = None
    contract_value: Optional[float] = None
    estimated_margin_pct: Optional[float] = None
    actual_margin_pct: Optional[float] = None
    general_contractor: Optional[str] = None
    project_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    square_footage: Optional[int] = None
    bid_due_date: Optional[str] = None
    estimated_start_date: Optional[str] = None
    estimated_end_date: Optional[str] = None
    actual_start_date: Optional[str] = None
    actual_end_date: Optional[str] = None
    win_probability: Optional[float] = None
    loss_reason: Optional[str] = None
    assigned_estimator: Optional[str] = None
    assigned_pm: Optional[str] = None
    notes: Optional[str] = None


class StageUpdate(BaseModel):
    stage: str
    loss_reason: Optional[str] = None


@router.get("")
def list_projects(
    stage: Optional[str] = None,
    customer_id: Optional[int] = None,
    project_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Project)
    if stage:
        q = q.filter(Project.stage == stage)
    if customer_id:
        q = q.filter(Project.customer_id == customer_id)
    if project_type:
        q = q.filter(Project.project_type == project_type)
    projects = q.order_by(Project.created_at.desc()).all()
    # Batch-load customer names to avoid N+1
    cust_ids = {p.customer_id for p in projects}
    cust_map = {
        c.id: c.name
        for c in db.query(Customer.id, Customer.name).filter(Customer.id.in_(cust_ids)).all()
    } if cust_ids else {}
    return [_to_dict(p, cust_map) for p in projects]


@router.get("/pipeline")
def pipeline_summary(db: Session = Depends(get_db)):
    """Counts and total value per pipeline stage."""
    stages = [
        "lead", "qualified", "estimating", "bid_submitted",
        "negotiation", "won", "lost", "in_progress", "completed", "cancelled",
    ]
    result = {}
    for stage in stages:
        row = (
            db.query(func.count(Project.id), func.coalesce(func.sum(Project.bid_amount), 0))
            .filter(Project.stage == stage)
            .first()
        )
        result[stage] = {"count": row[0], "total_value": row[1]}
    return result


@router.get("/win-loss")
def win_loss_analytics(db: Session = Depends(get_db)):
    won = db.query(func.count(Project.id)).filter(Project.stage == "won").scalar() or 0
    lost = db.query(func.count(Project.id)).filter(Project.stage == "lost").scalar() or 0
    total = won + lost
    win_rate = (won / total * 100) if total > 0 else 0

    # Loss reasons breakdown
    loss_reasons = (
        db.query(Project.loss_reason, func.count(Project.id))
        .filter(Project.stage == "lost", Project.loss_reason.isnot(None))
        .group_by(Project.loss_reason)
        .all()
    )
    return {
        "won": won,
        "lost": lost,
        "win_rate": round(win_rate, 1),
        "loss_reasons": {r: c for r, c in loss_reasons},
    }


def _cust_map_for(db: Session, *projects: Project) -> dict[int, str]:
    ids = {p.customer_id for p in projects}
    return {c.id: c.name for c in db.query(Customer.id, Customer.name).filter(Customer.id.in_(ids)).all()} if ids else {}


@router.get("/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return _to_dict(p, _cust_map_for(db, p))


@router.post("", status_code=201)
def create_project(body: ProjectCreate, db: Session = Depends(get_db)):
    p = Project(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_dict(p, _cust_map_for(db, p))


@router.put("/{project_id}")
def update_project(project_id: int, body: ProjectUpdate, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = _utcnow()
    db.commit()
    db.refresh(p)
    return _to_dict(p, _cust_map_for(db, p))


@router.patch("/{project_id}/stage")
def update_stage(project_id: int, body: StageUpdate, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    p.stage = body.stage
    if body.loss_reason:
        p.loss_reason = body.loss_reason
    p.updated_at = _utcnow()
    db.commit()
    db.refresh(p)
    return _to_dict(p, _cust_map_for(db, p))


def _to_dict(p: Project, cust_map: dict[int, str]) -> dict:
    return {
        "id": p.id,
        "customer_id": p.customer_id,
        "customer_name": cust_map.get(p.customer_id, ""),
        "name": p.name,
        "description": p.description,
        "project_type": p.project_type,
        "stage": p.stage,
        "priority": p.priority,
        "bid_amount": p.bid_amount,
        "estimated_cost": p.estimated_cost,
        "contract_value": p.contract_value,
        "estimated_margin_pct": p.estimated_margin_pct,
        "actual_margin_pct": p.actual_margin_pct,
        "general_contractor": p.general_contractor,
        "project_address": p.project_address,
        "city": p.city,
        "state": p.state,
        "square_footage": p.square_footage,
        "bid_due_date": p.bid_due_date,
        "estimated_start_date": p.estimated_start_date,
        "estimated_end_date": p.estimated_end_date,
        "actual_start_date": p.actual_start_date,
        "actual_end_date": p.actual_end_date,
        "win_probability": p.win_probability,
        "loss_reason": p.loss_reason,
        "assigned_estimator": p.assigned_estimator,
        "assigned_pm": p.assigned_pm,
        "notes": p.notes,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
