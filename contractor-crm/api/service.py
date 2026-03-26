from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import ServiceRecord, MaintenanceContract, _utcnow

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class ServiceRecordCreate(BaseModel):
    customer_id: int
    project_id: Optional[int] = None
    service_type: str
    status: str = "open"
    priority: str = "normal"
    description: Optional[str] = None
    location: Optional[str] = None
    scheduled_date: Optional[str] = None
    assigned_technician: Optional[str] = None
    is_warranty: int = 0


class ServiceRecordUpdate(BaseModel):
    service_type: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    scheduled_date: Optional[str] = None
    completed_date: Optional[str] = None
    assigned_technician: Optional[str] = None
    hours_worked: Optional[float] = None
    material_cost: Optional[float] = None
    labor_cost: Optional[float] = None
    total_invoice: Optional[float] = None
    is_warranty: Optional[int] = None
    customer_satisfaction: Optional[int] = None
    resolution_notes: Optional[str] = None


class ContractCreate(BaseModel):
    customer_id: int
    name: str
    contract_type: Optional[str] = None
    annual_value: Optional[float] = None
    start_date: str
    end_date: Optional[str] = None
    renewal_date: Optional[str] = None
    auto_renew: int = 0
    status: str = "active"
    scope_description: Optional[str] = None
    visit_frequency: Optional[str] = None
    notes: Optional[str] = None


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    contract_type: Optional[str] = None
    annual_value: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    renewal_date: Optional[str] = None
    auto_renew: Optional[int] = None
    status: Optional[str] = None
    scope_description: Optional[str] = None
    visit_frequency: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Service Records
# ---------------------------------------------------------------------------
@router.get("/records")
def list_service_records(
    customer_id: Optional[int] = None,
    service_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(ServiceRecord)
    if customer_id:
        q = q.filter(ServiceRecord.customer_id == customer_id)
    if service_type:
        q = q.filter(ServiceRecord.service_type == service_type)
    if status:
        q = q.filter(ServiceRecord.status == status)
    return [_sr_dict(r) for r in q.order_by(ServiceRecord.created_at.desc()).all()]


@router.get("/records/{record_id}")
def get_service_record(record_id: int, db: Session = Depends(get_db)):
    r = db.query(ServiceRecord).filter(ServiceRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Service record not found")
    return _sr_dict(r)


@router.post("/records", status_code=201)
def create_service_record(body: ServiceRecordCreate, db: Session = Depends(get_db)):
    r = ServiceRecord(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _sr_dict(r)


@router.put("/records/{record_id}")
def update_service_record(record_id: int, body: ServiceRecordUpdate, db: Session = Depends(get_db)):
    r = db.query(ServiceRecord).filter(ServiceRecord.id == record_id).first()
    if not r:
        raise HTTPException(404, "Service record not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    r.updated_at = _utcnow()
    db.commit()
    db.refresh(r)
    return _sr_dict(r)


# ---------------------------------------------------------------------------
# Maintenance Contracts
# ---------------------------------------------------------------------------
@router.get("/contracts")
def list_contracts(
    customer_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(MaintenanceContract)
    if customer_id:
        q = q.filter(MaintenanceContract.customer_id == customer_id)
    if status:
        q = q.filter(MaintenanceContract.status == status)
    return [_mc_dict(c) for c in q.order_by(MaintenanceContract.renewal_date).all()]


@router.get("/contracts/renewals")
def upcoming_renewals(db: Session = Depends(get_db)):
    """Contracts with renewal dates in the next 90 days."""
    from datetime import datetime, timedelta
    now = datetime.now().strftime("%Y-%m-%d")
    future = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
    rows = (
        db.query(MaintenanceContract)
        .filter(
            MaintenanceContract.renewal_date.isnot(None),
            MaintenanceContract.renewal_date >= now,
            MaintenanceContract.renewal_date <= future,
            MaintenanceContract.status == "active",
        )
        .order_by(MaintenanceContract.renewal_date)
        .all()
    )
    return [_mc_dict(c) for c in rows]


@router.post("/contracts", status_code=201)
def create_contract(body: ContractCreate, db: Session = Depends(get_db)):
    c = MaintenanceContract(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _mc_dict(c)


@router.put("/contracts/{contract_id}")
def update_contract(contract_id: int, body: ContractUpdate, db: Session = Depends(get_db)):
    c = db.query(MaintenanceContract).filter(MaintenanceContract.id == contract_id).first()
    if not c:
        raise HTTPException(404, "Contract not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    c.updated_at = _utcnow()
    db.commit()
    db.refresh(c)
    return _mc_dict(c)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _sr_dict(r: ServiceRecord) -> dict:
    return {
        "id": r.id,
        "customer_id": r.customer_id,
        "project_id": r.project_id,
        "service_type": r.service_type,
        "status": r.status,
        "priority": r.priority,
        "description": r.description,
        "location": r.location,
        "scheduled_date": r.scheduled_date,
        "completed_date": r.completed_date,
        "assigned_technician": r.assigned_technician,
        "hours_worked": r.hours_worked,
        "material_cost": r.material_cost,
        "labor_cost": r.labor_cost,
        "total_invoice": r.total_invoice,
        "is_warranty": r.is_warranty,
        "customer_satisfaction": r.customer_satisfaction,
        "resolution_notes": r.resolution_notes,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _mc_dict(c: MaintenanceContract) -> dict:
    return {
        "id": c.id,
        "customer_id": c.customer_id,
        "name": c.name,
        "contract_type": c.contract_type,
        "annual_value": c.annual_value,
        "start_date": c.start_date,
        "end_date": c.end_date,
        "renewal_date": c.renewal_date,
        "auto_renew": c.auto_renew,
        "status": c.status,
        "scope_description": c.scope_description,
        "visit_frequency": c.visit_frequency,
        "notes": c.notes,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }
