from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Interaction, Contact, _utcnow

router = APIRouter()


class InteractionCreate(BaseModel):
    customer_id: int
    contact_id: Optional[int] = None
    project_id: Optional[int] = None
    interaction_type: str
    direction: Optional[str] = None
    subject: Optional[str] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None
    interaction_date: str
    follow_up_date: Optional[str] = None
    logged_by: Optional[str] = None


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    direction: Optional[str] = None
    subject: Optional[str] = None
    summary: Optional[str] = None
    outcome: Optional[str] = None
    interaction_date: Optional[str] = None
    follow_up_date: Optional[str] = None
    follow_up_completed: Optional[int] = None
    logged_by: Optional[str] = None


@router.get("")
def list_interactions(
    customer_id: Optional[int] = None,
    contact_id: Optional[int] = None,
    interaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Interaction)
    if customer_id:
        q = q.filter(Interaction.customer_id == customer_id)
    if contact_id:
        q = q.filter(Interaction.contact_id == contact_id)
    if interaction_type:
        q = q.filter(Interaction.interaction_type == interaction_type)
    return [_to_dict(i) for i in q.order_by(Interaction.interaction_date.desc()).all()]


@router.get("/overdue-followups")
def overdue_followups(db: Session = Depends(get_db)):
    now = _utcnow()[:10]  # YYYY-MM-DD
    rows = (
        db.query(Interaction)
        .filter(
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_completed == 0,
            Interaction.follow_up_date <= now,
        )
        .order_by(Interaction.follow_up_date)
        .all()
    )
    return [_to_dict(i) for i in rows]


@router.post("", status_code=201)
def create_interaction(body: InteractionCreate, db: Session = Depends(get_db)):
    i = Interaction(**body.model_dump())
    db.add(i)
    # Update contact's last_contact_date
    if body.contact_id:
        contact = db.query(Contact).filter(Contact.id == body.contact_id).first()
        if contact:
            contact.last_contact_date = body.interaction_date
    db.commit()
    db.refresh(i)
    return _to_dict(i)


@router.put("/{interaction_id}")
def update_interaction(interaction_id: int, body: InteractionUpdate, db: Session = Depends(get_db)):
    i = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not i:
        raise HTTPException(404, "Interaction not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(i, k, v)
    db.commit()
    db.refresh(i)
    return _to_dict(i)


def _to_dict(i: Interaction) -> dict:
    return {
        "id": i.id,
        "customer_id": i.customer_id,
        "contact_id": i.contact_id,
        "project_id": i.project_id,
        "interaction_type": i.interaction_type,
        "direction": i.direction,
        "subject": i.subject,
        "summary": i.summary,
        "outcome": i.outcome,
        "interaction_date": i.interaction_date,
        "follow_up_date": i.follow_up_date,
        "follow_up_completed": i.follow_up_completed,
        "logged_by": i.logged_by,
        "created_at": i.created_at,
    }
