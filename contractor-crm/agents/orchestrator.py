"""Multi-agent orchestrator for batch analysis and daily digests."""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from agents.base import chat, parse_json_response
from db.models import Customer, Prospect
from services.concentration import concentration_analysis
from services.scoring import refresh_all_scores


CONCENTRATION_SYSTEM_PROMPT = """You are a business strategist for a $50M commercial electrical contractor.
Analyze the revenue concentration data and provide strategic recommendations
to reduce risk and diversify the customer base.

Respond with a JSON object:
{
    "risk_level": "low|moderate|high|critical",
    "key_insights": ["list of observations about the concentration"],
    "immediate_actions": ["actions to take in the next 30 days"],
    "strategic_recommendations": ["longer-term strategies for diversification"],
    "target_segments": ["industry segments to pursue for diversification"],
    "summary": "2-3 sentence executive summary"
}"""


GROWTH_SYSTEM_PROMPT = """You are a business development strategist for a $50M commercial electrical contractor.
Given the current customer base and prospect pipeline, prioritize prospects
and recommend growth strategies.

Respond with a JSON object:
{
    "priority_prospects": [
        {
            "prospect_name": "name",
            "priority": "high|medium|low",
            "reasoning": "why to pursue this prospect",
            "approach": "suggested outreach strategy"
        }
    ],
    "segment_opportunities": ["underserved segments with growth potential"],
    "strategic_recommendations": ["overall growth strategy recommendations"],
    "summary": "2-3 sentence executive summary"
}"""


def concentration_review(db: Session) -> dict:
    """AI-powered concentration analysis with strategic recommendations."""
    from datetime import datetime
    current_year = datetime.now().year
    analysis = concentration_analysis(db, current_year)

    if analysis["total_revenue"] == 0:
        analysis = concentration_analysis(db)

    response_text = chat(
        CONCENTRATION_SYSTEM_PROMPT,
        f"Revenue concentration data:\n{json.dumps(analysis, indent=2)}",
    )
    result = parse_json_response(response_text)
    result["concentration_data"] = analysis
    return result


def growth_priorities(db: Session) -> dict:
    """AI-ranked prospect priorities and growth strategy."""
    customers = db.query(Customer).filter(Customer.status == "active").all()
    prospects = db.query(Prospect).filter(Prospect.converted_customer_id.is_(None)).all()

    context = {
        "current_customers": [
            {
                "name": c.name,
                "type": c.customer_type,
                "segment": c.industry_segment,
                "tier": c.relationship_tier,
                "revenue_potential": c.annual_revenue_potential,
            }
            for c in customers
        ],
        "prospects": [
            {
                "name": p.company_name,
                "type": p.prospect_type,
                "segment": p.industry_segment,
                "estimated_spend": p.estimated_annual_spend,
                "outreach_status": p.outreach_status,
                "priority_score": p.priority_score,
                "city": p.city,
                "state": p.state,
            }
            for p in prospects
        ],
        "customer_count": len(customers),
        "prospect_count": len(prospects),
    }

    response_text = chat(
        GROWTH_SYSTEM_PROMPT,
        json.dumps(context, indent=2),
    )
    return parse_json_response(response_text)
