from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.database import get_db
from db.models import Contact, _utcnow

router = APIRouter()


class ContactCreate(BaseModel):
    customer_id: int
    first_name: str
    last_name: str
    title: Optional[str] = None
    role_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    is_primary: int = 0
    relationship_owner: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None


class ContactUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None
    role_type: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    mobile: Optional[str] = None
    is_primary: Optional[int] = None
    relationship_owner: Optional[str] = None
    preferred_contact_method: Optional[str] = None
    notes: Optional[str] = None


@router.get("")
def list_contacts(
    customer_id: Optional[int] = None,
    role_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Contact)
    if customer_id:
        q = q.filter(Contact.customer_id == customer_id)
    if role_type:
        q = q.filter(Contact.role_type == role_type)
    return [_to_dict(c) for c in q.order_by(Contact.last_name).all()]


@router.get("/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(404, "Contact not found")
    return _to_dict(c)


@router.post("", status_code=201)
def create_contact(body: ContactCreate, db: Session = Depends(get_db)):
    c = Contact(**body.model_dump())
    db.add(c)
    db.commit()
    db.refresh(c)
    return _to_dict(c)


@router.put("/{contact_id}")
def update_contact(contact_id: int, body: ContactUpdate, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(404, "Contact not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    c.updated_at = _utcnow()
    db.commit()
    db.refresh(c)
    return _to_dict(c)


@router.delete("/{contact_id}")
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    c = db.query(Contact).filter(Contact.id == contact_id).first()
    if not c:
        raise HTTPException(404, "Contact not found")
    db.delete(c)
    db.commit()
    return {"status": "deleted", "id": contact_id}


def _to_dict(c: Contact) -> dict:
    return {
        "id": c.id,
        "customer_id": c.customer_id,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "title": c.title,
        "role_type": c.role_type,
        "email": c.email,
        "phone": c.phone,
        "mobile": c.mobile,
        "is_primary": c.is_primary,
        "relationship_owner": c.relationship_owner,
        "last_contact_date": c.last_contact_date,
        "preferred_contact_method": c.preferred_contact_method,
        "notes": c.notes,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
    }
