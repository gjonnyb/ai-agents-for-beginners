"""AI agent for next-best-action recommendations."""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from agents.base import chat, parse_json_response
from db.models import (
    Contact,
    Customer,
    Interaction,
    MaintenanceContract,
    Project,
)
from services.scoring import score_customer


SYSTEM_PROMPT = """You are a sales strategy advisor for a $50M commercial electrical contractor.
Given a customer's relationship data, recommend the most impactful next actions to
strengthen the relationship and grow the account.

Consider actions like:
- Scheduling a site visit or lunch meeting
- Sending a proposal for additional scope or new project
- Introducing contacts to senior leadership
- Following up on outstanding quotes or bids
- Proposing a maintenance contract
- Sending appreciation notes or holiday gifts
- Inviting to industry events or company open houses
- Asking for referrals (only for strong relationships)
- Addressing any open service issues promptly

Respond with a JSON object:
{
    "actions": [
        {
            "action": "description of the action",
            "priority": "high|medium|low",
            "reasoning": "why this action matters",
            "timeline": "when to do it (e.g., 'this week', 'within 30 days')",
            "owner_suggestion": "who should execute (e.g., 'salesperson', 'PM', 'VP')"
        }
    ],
    "account_strategy": "1-2 sentence overall strategy for this account"
}"""


def recommend_next_actions(customer_id: int, db: Session) -> dict:
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    contacts = db.query(Contact).filter(Contact.customer_id == customer_id).all()
    interactions = (
        db.query(Interaction)
        .filter(Interaction.customer_id == customer_id)
        .order_by(Interaction.interaction_date.desc())
        .limit(20)
        .all()
    )
    projects = db.query(Project).filter(Project.customer_id == customer_id).all()
    contracts = (
        db.query(MaintenanceContract)
        .filter(MaintenanceContract.customer_id == customer_id)
        .all()
    )
    scoring = score_customer(customer_id, db)

    # Overdue follow-ups
    from db.models import _utcnow
    now = _utcnow()[:10]
    overdue = (
        db.query(Interaction)
        .filter(
            Interaction.customer_id == customer_id,
            Interaction.follow_up_date.isnot(None),
            Interaction.follow_up_completed == 0,
            Interaction.follow_up_date <= now,
        )
        .all()
    )

    context = {
        "customer": {
            "name": customer.name,
            "type": customer.customer_type,
            "segment": customer.industry_segment,
            "score": scoring["score"],
            "tier": scoring["tier"],
            "score_breakdown": scoring["breakdown"],
        },
        "contacts": [
            {"name": f"{c.first_name} {c.last_name}", "title": c.title, "role": c.role_type}
            for c in contacts
        ],
        "recent_interactions": [
            {"type": i.interaction_type, "date": i.interaction_date, "subject": i.subject}
            for i in interactions
        ],
        "active_projects": [
            {"name": p.name, "type": p.project_type, "stage": p.stage, "value": p.bid_amount}
            for p in projects if p.stage in ("lead", "qualified", "estimating", "bid_submitted", "negotiation", "won", "in_progress")
        ],
        "maintenance_contracts": [
            {"name": c.name, "status": c.status, "renewal_date": c.renewal_date}
            for c in contracts
        ],
        "overdue_followups": [
            {"subject": o.subject, "follow_up_date": o.follow_up_date}
            for o in overdue
        ],
    }

    response_text = chat(SYSTEM_PROMPT, json.dumps(context, indent=2))
    result = parse_json_response(response_text)
    result["customer_id"] = customer_id
    result["customer_name"] = customer.name
    return result
