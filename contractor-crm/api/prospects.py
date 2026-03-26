from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Prospect, Customer, Contact, _utcnow

router = APIRouter()


class ProspectCreate(BaseModel):
    company_name: str
    industry_segment: Optional[str] = None
    prospect_type: Optional[str] = None
    estimated_annual_spend: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    key_contact_name: Optional[str] = None
    key_contact_title: Optional[str] = None
    key_contact_email: Optional[str] = None
    key_contact_phone: Optional[str] = None
    outreach_status: str = "identified"
    assigned_to: Optional[str] = None
    priority_score: float = 0.0
    conversion_notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None


class ProspectUpdate(BaseModel):
    company_name: Optional[str] = None
    industry_segment: Optional[str] = None
    prospect_type: Optional[str] = None
    estimated_annual_spend: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    website: Optional[str] = None
    key_contact_name: Optional[str] = None
    key_contact_title: Optional[str] = None
    key_contact_email: Optional[str] = None
    key_contact_phone: Optional[str] = None
    outreach_status: Optional[str] = None
    assigned_to: Optional[str] = None
    priority_score: Optional[float] = None
    conversion_notes: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[str] = None


@router.get("")
def list_prospects(
    outreach_status: Optional[str] = None,
    industry_segment: Optional[str] = None,
    assigned_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Prospect).filter(Prospect.converted_customer_id.is_(None))
    if outreach_status:
        q = q.filter(Prospect.outreach_status == outreach_status)
    if industry_segment:
        q = q.filter(Prospect.industry_segment == industry_segment)
    if assigned_to:
        q = q.filter(Prospect.assigned_to == assigned_to)
    return [_to_dict(p) for p in q.order_by(Prospect.priority_score.desc()).all()]


@router.get("/{prospect_id}")
def get_prospect(prospect_id: int, db: Session = Depends(get_db)):
    p = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not p:
        raise HTTPException(404, "Prospect not found")
    return _to_dict(p)


@router.post("", status_code=201)
def create_prospect(body: ProspectCreate, db: Session = Depends(get_db)):
    p = Prospect(**body.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return _to_dict(p)


@router.put("/{prospect_id}")
def update_prospect(prospect_id: int, body: ProspectUpdate, db: Session = Depends(get_db)):
    p = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not p:
        raise HTTPException(404, "Prospect not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    p.updated_at = _utcnow()
    db.commit()
    db.refresh(p)
    return _to_dict(p)


@router.post("/{prospect_id}/convert", status_code=201)
def convert_prospect(prospect_id: int, db: Session = Depends(get_db)):
    """Convert a prospect into a customer and primary contact."""
    p = db.query(Prospect).filter(Prospect.id == prospect_id).first()
    if not p:
        raise HTTPException(404, "Prospect not found")
    if p.converted_customer_id:
        raise HTTPException(400, "Prospect already converted")

    # Create customer
    customer = Customer(
        name=p.company_name,
        customer_type=p.prospect_type or "other",
        status="active",
        industry_segment=p.industry_segment,
        city=p.city,
        state=p.state,
        website=p.website,
        annual_revenue_potential=p.estimated_annual_spend,
        source="cold_outreach",
    )
    db.add(customer)
    db.flush()

    # Create primary contact if we have contact info
    if p.key_contact_name:
        parts = p.key_contact_name.split(" ", 1)
        first = parts[0]
        last = parts[1] if len(parts) > 1 else ""
        contact = Contact(
            customer_id=customer.id,
            first_name=first,
            last_name=last,
            title=p.key_contact_title,
            email=p.key_contact_email,
            phone=p.key_contact_phone,
            is_primary=1,
            role_type="decision_maker",
        )
        db.add(contact)

    p.converted_customer_id = customer.id
    p.outreach_status = "converted"
    p.updated_at = _utcnow()
    db.commit()
    db.refresh(customer)

    return {
        "status": "converted",
        "prospect_id": prospect_id,
        "customer_id": customer.id,
        "customer_name": customer.name,
    }


def _to_dict(p: Prospect) -> dict:
    return {
        "id": p.id,
        "company_name": p.company_name,
        "industry_segment": p.industry_segment,
        "prospect_type": p.prospect_type,
        "estimated_annual_spend": p.estimated_annual_spend,
        "city": p.city,
        "state": p.state,
        "website": p.website,
        "key_contact_name": p.key_contact_name,
        "key_contact_title": p.key_contact_title,
        "key_contact_email": p.key_contact_email,
        "key_contact_phone": p.key_contact_phone,
        "outreach_status": p.outreach_status,
        "assigned_to": p.assigned_to,
        "priority_score": p.priority_score,
        "conversion_notes": p.conversion_notes,
        "next_action": p.next_action,
        "next_action_date": p.next_action_date,
        "converted_customer_id": p.converted_customer_id,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }
