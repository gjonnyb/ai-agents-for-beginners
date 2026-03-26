"""AI agent for deep relationship health analysis."""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from agents.base import chat
from db.models import (
    Contact,
    Customer,
    Interaction,
    MaintenanceContract,
    Project,
    RevenueRecord,
    ServiceRecord,
)
from services.scoring import score_customer


SYSTEM_PROMPT = """You are a relationship intelligence analyst for a $50M commercial electrical contractor.
Your job is to analyze the full relationship data for a customer and produce actionable insights.

You deeply understand the commercial electrical contracting business:
- Relationships with general contractors, property managers, facility managers, and developers are the lifeblood of the business.
- Repeat work and referrals are the highest-margin revenue sources.
- Service/maintenance contracts create recurring revenue and ongoing touchpoints.
- Losing a large customer to a competitor can take years to replace.

Respond with a JSON object containing:
{
    "health_status": "strong|healthy|at_risk|critical",
    "risk_score": 0-100 (0 = no risk, 100 = imminent loss),
    "strengths": ["list of relationship strengths"],
    "risks": ["list of risk factors or warning signs"],
    "recommendations": ["specific, actionable recommendations to strengthen the relationship"],
    "summary": "2-3 sentence executive summary"
}"""


def analyze_relationship(customer_id: int, db: Session) -> dict:
    """Run a deep relationship analysis for one customer."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return {"error": "Customer not found"}

    # Gather all relevant data
    contacts = db.query(Contact).filter(Contact.customer_id == customer_id).all()
    interactions = (
        db.query(Interaction)
        .filter(Interaction.customer_id == customer_id)
        .order_by(Interaction.interaction_date.desc())
        .limit(50)
        .all()
    )
    projects = db.query(Project).filter(Project.customer_id == customer_id).all()
    service_records = (
        db.query(ServiceRecord)
        .filter(ServiceRecord.customer_id == customer_id)
        .order_by(ServiceRecord.created_at.desc())
        .limit(20)
        .all()
    )
    contracts = (
        db.query(MaintenanceContract)
        .filter(MaintenanceContract.customer_id == customer_id)
        .all()
    )
    total_revenue = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0))
        .filter(RevenueRecord.customer_id == customer_id)
        .scalar()
    )
    scoring = score_customer(customer_id, db)

    # Build context for the LLM
    context = {
        "customer": {
            "name": customer.name,
            "type": customer.customer_type,
            "segment": customer.industry_segment,
            "status": customer.status,
            "relationship_score": scoring["score"],
            "tier": scoring["tier"],
            "score_breakdown": scoring["breakdown"],
            "total_revenue": total_revenue,
        },
        "contacts": [
            {
                "name": f"{c.first_name} {c.last_name}",
                "title": c.title,
                "role": c.role_type,
                "is_primary": bool(c.is_primary),
                "last_contact": c.last_contact_date,
            }
            for c in contacts
        ],
        "recent_interactions": [
            {
                "type": i.interaction_type,
                "date": i.interaction_date,
                "subject": i.subject,
                "direction": i.direction,
                "outcome": i.outcome,
            }
            for i in interactions[:20]
        ],
        "projects": [
            {
                "name": p.name,
                "type": p.project_type,
                "stage": p.stage,
                "value": p.contract_value or p.bid_amount,
                "win_probability": p.win_probability,
                "loss_reason": p.loss_reason,
            }
            for p in projects
        ],
        "service_history": [
            {
                "type": s.service_type,
                "status": s.status,
                "satisfaction": s.customer_satisfaction,
                "is_warranty": bool(s.is_warranty),
            }
            for s in service_records
        ],
        "maintenance_contracts": [
            {
                "name": c.name,
                "type": c.contract_type,
                "annual_value": c.annual_value,
                "status": c.status,
                "renewal_date": c.renewal_date,
            }
            for c in contracts
        ],
    }

    user_prompt = (
        f"Analyze the relationship health for this customer:\n\n"
        f"{json.dumps(context, indent=2)}"
    )

    response_text = chat(SYSTEM_PROMPT, user_prompt)

    # Parse JSON from response
    try:
        # Handle markdown code blocks
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
        result = json.loads(text)
    except json.JSONDecodeError:
        result = {"raw_response": response_text}

    result["customer_id"] = customer_id
    result["customer_name"] = customer.name
    result["relationship_score"] = scoring["score"]
    result["tier"] = scoring["tier"]
    return result
