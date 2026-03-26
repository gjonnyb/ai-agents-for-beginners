"""AI agent for bid/no-bid decision support."""
from __future__ import annotations

import json

from sqlalchemy import func
from sqlalchemy.orm import Session

from agents.base import chat, parse_json_response
from db.models import Customer, Project, RevenueRecord
from services.scoring import score_customer


SYSTEM_PROMPT = """You are a bid strategy advisor for a $50M commercial electrical contractor.
Given a project opportunity and the customer context, recommend whether to bid, not bid,
or bid with conditions.

Consider factors like:
- Customer relationship strength and history
- Project type and our win rate for similar projects
- Estimated margin vs company targets (typical target: 12-18%)
- Current workload and capacity
- Strategic value (new market segment, new customer, reference project)
- Competitive dynamics
- Payment/credit risk
- Scope clarity and risk

Respond with a JSON object:
{
    "recommendation": "bid|no_bid|bid_with_conditions",
    "confidence": 0.0-1.0,
    "key_factors": ["list of factors driving the recommendation"],
    "risks": ["list of risks to watch if we bid"],
    "bid_strategy": "aggressive|competitive|premium",
    "strategy_rationale": "why this pricing strategy",
    "conditions": ["conditions that should be met, if bid_with_conditions"],
    "summary": "2-3 sentence executive summary"
}"""


def analyze_bid(project_id: int, db: Session) -> dict:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "Project not found"}

    customer = db.query(Customer).filter(Customer.id == project.customer_id).first()
    scoring = score_customer(project.customer_id, db) if customer else {}

    # Win rate for this project type
    won = (
        db.query(func.count(Project.id))
        .filter(Project.stage == "won", Project.project_type == project.project_type)
        .scalar()
    ) or 0
    lost = (
        db.query(func.count(Project.id))
        .filter(Project.stage == "lost", Project.project_type == project.project_type)
        .scalar()
    ) or 0
    type_win_rate = round(won / (won + lost) * 100, 1) if (won + lost) > 0 else None

    # Customer history
    cust_projects = db.query(Project).filter(Project.customer_id == project.customer_id).all()
    cust_won = sum(1 for p in cust_projects if p.stage == "won")
    cust_lost = sum(1 for p in cust_projects if p.stage == "lost")
    cust_revenue = (
        db.query(func.coalesce(func.sum(RevenueRecord.amount), 0))
        .filter(RevenueRecord.customer_id == project.customer_id)
        .scalar()
    )

    # Current workload
    active_count = (
        db.query(func.count(Project.id))
        .filter(Project.stage.in_(["won", "in_progress"]))
        .scalar()
    )

    context = {
        "project": {
            "name": project.name,
            "type": project.project_type,
            "description": project.description,
            "bid_amount": project.bid_amount,
            "estimated_cost": project.estimated_cost,
            "estimated_margin": project.estimated_margin_pct,
            "square_footage": project.square_footage,
            "general_contractor": project.general_contractor,
            "bid_due_date": project.bid_due_date,
            "location": f"{project.city}, {project.state}" if project.city else None,
        },
        "customer": {
            "name": customer.name if customer else "Unknown",
            "type": customer.customer_type if customer else None,
            "relationship_score": scoring.get("score"),
            "tier": scoring.get("tier"),
            "total_revenue_with_us": cust_revenue,
            "projects_won": cust_won,
            "projects_lost": cust_lost,
        },
        "analytics": {
            "win_rate_for_project_type": type_win_rate,
            "current_active_projects": active_count,
        },
    }

    response_text = chat(SYSTEM_PROMPT, json.dumps(context, indent=2))
    result = parse_json_response(response_text)
    result["project_id"] = project_id
    result["project_name"] = project.name
    result["customer_name"] = customer.name if customer else "Unknown"
    return result
