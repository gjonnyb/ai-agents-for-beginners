from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Customer, Contact, Project, Interaction, RevenueRecord, _utcnow

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class CustomerCreate(BaseModel):
    name: str
    customer_type: str
    status: str = "active"
    industry_segment: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    annual_revenue_potential: Optional[float] = None
    source: Optional[str] = None
    notes: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    customer_type: Optional[str] = None
    status: Optional[str] = None
    industry_segment: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    annual_revenue_potential: Optional[float] = None
    source: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@router.get("")
def list_customers(
    status: Optional[str] = None,
    customer_type: Optional[str] = None,
    industry_segment: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query(default="name"),
    db: Session = Depends(get_db),
):
    q = db.query(Customer)
    if status:
        q = q.filter(Customer.status == status)
    if customer_type:
        q = q.filter(Customer.customer_type == customer_type)
    if industry_segment:
        q = q.filter(Customer.industry_segment == industry_segment)
    if search:
        q = q.filter(Customer.name.ilike(f"%{search}%"))

    sort_col = getattr(Customer, sort_by, Customer.name)
    q = q.order_by(sort_col)
    rows = q.all()
    return [_customer_to_dict(c) for c in rows]


@router.get("/{customer_id}")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    data = _customer_to_dict(c)
    data["contacts"] = [_contact_summary(ct) for ct in c.contacts]
    data["recent_projects"] = [
        _project_summary(p)
        for p in sorted(c.projects, key=lambda p: p.created_at or "", reverse=True)[:10]
    ]
    # Revenue summary
    from sqlalchemy import func
    rev = (
        db.query(func.sum(RevenueRecord.amount))
        .filter(RevenueRecord.customer_id == customer_id)
        .scalar()
    ) or 0.0
    data["total_revenue"] = rev
    return data


@router.post("", status_code=201)
def create_customer(body: CustomerCreate, db: Session = Depends(get_db)):
    c = Customer(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _customer_to_dict(c)


@router.put("/{customer_id}")
def update_customer(customer_id: int, body: CustomerUpdate, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    c.updated_at = _utcnow()
    db.commit()
    db.refresh(c)
    return _customer_to_dict(c)


@router.delete("/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db)):
    c = db.query(Customer).filter(Customer.id == customer_id).first()
    if not c:
        raise HTTPException(404, "Customer not found")
    c.status = "inactive"
    c.updated_at = _utcnow()
    db.commit()
    return {"status": "deactivated", "id": customer_id}


@router.get("/{customer_id}/revenue")
def customer_revenue(customer_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(RevenueRecord)
        .filter(RevenueRecord.customer_id == customer_id)
        .order_by(RevenueRecord.invoice_date.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "revenue_type": r.revenue_type,
            "amount": r.amount,
            "cost": r.cost,
            "invoice_date": r.invoice_date,
            "fiscal_year": r.fiscal_year,
            "fiscal_quarter": r.fiscal_quarter,
            "notes": r.notes,
        }
        for r in rows
    ]


@router.get("/{customer_id}/timeline")
def customer_timeline(customer_id: int, db: Session = Depends(get_db)):
    """Combined timeline of interactions, projects, and service records."""
    interactions = (
        db.query(Interaction)
        .filter(Interaction.customer_id == customer_id)
        .all()
    )
    projects = (
        db.query(Project)
        .filter(Project.customer_id == customer_id)
        .all()
    )
    events = []
    for i in interactions:
        events.append({
            "type": "interaction",
            "date": i.interaction_date,
            "subtype": i.interaction_type,
            "summary": i.subject or i.summary or "",
            "id": i.id,
        })
    for p in projects:
        events.append({
            "type": "project",
            "date": p.created_at,
            "subtype": p.stage,
            "summary": p.name,
            "id": p.id,
        })
    events.sort(key=lambda e: e["date"] or "", reverse=True)
    return events


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _customer_to_dict(c: Customer) -> dict:
    return {
        "id": c.id,
        "name": c.name,
        "customer_type": c.customer_type,
        "status": c.status,
        "industry_segment": c.industry_segment,
        "address_line1": c.address_line1,
        "address_line2": c.address_line2,
        "city": c.city,
        "state": c.state,
        "zip_code": c.zip_code,
        "phone": c.phone,
        "email": c.email,
        "website": c.website,
        "annual_revenue_potential": c.annual_revenue_potential,
        "relationship_score": c.relationship_score,
        "relationship_tier": c.relationship_tier,
        "source": c.source,
        "notes": c.notes,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }


def _contact_summary(ct: Contact) -> dict:
    return {
        "id": ct.id,
        "first_name": ct.first_name,
        "last_name": ct.last_name,
        "title": ct.title,
        "role_type": ct.role_type,
        "email": ct.email,
        "phone": ct.phone,
        "is_primary": ct.is_primary,
    }


def _project_summary(p: Project) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "project_type": p.project_type,
        "stage": p.stage,
        "contract_value": p.contract_value,
        "bid_amount": p.bid_amount,
    }
