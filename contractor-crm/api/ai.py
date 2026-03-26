from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config.settings import get_settings
from db.database import get_db
from db.models import AIRecommendation, _utcnow

router = APIRouter()


class RecommendationUpdate(BaseModel):
    status: str  # accepted, dismissed, completed
    acted_on_by: Optional[str] = None


@router.get("/status")
def ai_status():
    """Check whether an LLM API key is configured (never exposes the key)."""
    settings = get_settings()
    anthropic_ok = bool(settings.anthropic_api_key)
    openai_ok = bool(settings.openai_api_key)
    return {
        "ai_enabled": anthropic_ok or openai_ok,
        "provider": "anthropic" if anthropic_ok else ("openai" if openai_ok else None),
        "anthropic_configured": anthropic_ok,
        "openai_configured": openai_ok,
    }


@router.post("/relationship-analysis/{customer_id}")
def relationship_analysis(customer_id: int, db: Session = Depends(get_db)):
    try:
        from agents.relationship_agent import analyze_relationship
        result = analyze_relationship(customer_id, db)

        # Store as recommendation
        if "health_status" in result:
            rec = AIRecommendation(
                recommendation_type="relationship_health",
                entity_type="customer",
                entity_id=customer_id,
                title=f"Relationship Analysis: {result.get('customer_name', '')}",
                detail=result.get("summary", str(result)),
                priority="high" if result.get("health_status") in ("at_risk", "critical") else "medium",
                confidence=1.0 - (result.get("risk_score", 50) / 100),
            )
            db.add(rec)
            db.commit()

        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/next-actions/{customer_id}")
def next_actions(customer_id: int, db: Session = Depends(get_db)):
    try:
        from agents.next_action_agent import recommend_next_actions
        result = recommend_next_actions(customer_id, db)

        # Store recommendations
        for action in result.get("actions", []):
            rec = AIRecommendation(
                recommendation_type="next_action",
                entity_type="customer",
                entity_id=customer_id,
                title=action.get("action", ""),
                detail=action.get("reasoning", ""),
                priority=action.get("priority", "medium"),
            )
            db.add(rec)
        db.commit()

        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/bid-analysis/{project_id}")
def bid_analysis(project_id: int, db: Session = Depends(get_db)):
    try:
        from agents.bid_analysis_agent import analyze_bid
        result = analyze_bid(project_id, db)

        if "recommendation" in result:
            rec = AIRecommendation(
                recommendation_type="bid_analysis",
                entity_type="project",
                entity_id=project_id,
                title=f"Bid Analysis: {result.get('project_name', '')} — {result.get('recommendation', '')}",
                detail=result.get("summary", str(result)),
                priority="high" if result.get("recommendation") == "no_bid" else "medium",
                confidence=result.get("confidence"),
            )
            db.add(rec)
            db.commit()

        return result
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.get("/recommendations")
def list_recommendations(
    recommendation_type: Optional[str] = None,
    status: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(AIRecommendation)
    if recommendation_type:
        q = q.filter(AIRecommendation.recommendation_type == recommendation_type)
    if status:
        q = q.filter(AIRecommendation.status == status)
    if entity_type:
        q = q.filter(AIRecommendation.entity_type == entity_type)
    if entity_id:
        q = q.filter(AIRecommendation.entity_id == entity_id)
    rows = q.order_by(AIRecommendation.generated_at.desc()).limit(50).all()
    return [_rec_dict(r) for r in rows]


@router.patch("/recommendations/{rec_id}")
def update_recommendation(rec_id: int, body: RecommendationUpdate, db: Session = Depends(get_db)):
    r = db.query(AIRecommendation).filter(AIRecommendation.id == rec_id).first()
    if not r:
        raise HTTPException(404, "Recommendation not found")
    r.status = body.status
    r.acted_on_at = _utcnow()
    if body.acted_on_by:
        r.acted_on_by = body.acted_on_by
    db.commit()
    return _rec_dict(r)


@router.post("/concentration-review")
def concentration_review_endpoint(db: Session = Depends(get_db)):
    try:
        from agents.orchestrator import concentration_review
        return concentration_review(db)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/growth-priorities")
def growth_priorities_endpoint(db: Session = Depends(get_db)):
    try:
        from agents.orchestrator import growth_priorities
        return growth_priorities(db)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


def _rec_dict(r: AIRecommendation) -> dict:
    return {
        "id": r.id,
        "recommendation_type": r.recommendation_type,
        "entity_type": r.entity_type,
        "entity_id": r.entity_id,
        "title": r.title,
        "detail": r.detail,
        "priority": r.priority,
        "status": r.status,
        "confidence": r.confidence,
        "generated_at": r.generated_at,
        "acted_on_at": r.acted_on_at,
        "acted_on_by": r.acted_on_by,
    }
