"""Agent runs router — list and inspect agent execution history."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, distinct
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import AgentRunResponse
from packages.database.models.agent_run import AgentRun

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/runs", response_model=list[AgentRunResponse])
def list_agent_runs(
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List agent runs with optional filtering."""
    query = db.query(AgentRun)

    if agent_name:
        query = query.filter(AgentRun.agent_name == agent_name)
    if status:
        query = query.filter(AgentRun.status == status)

    runs = (
        query.order_by(desc(AgentRun.started_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return runs


@router.get("/runs/{run_id}", response_model=AgentRunResponse)
def get_agent_run(run_id: str, db: Session = Depends(get_db)):
    """Get details of a specific agent run."""
    run = db.query(AgentRun).filter(AgentRun.run_id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


@router.get("/summary")
def agent_summary(db: Session = Depends(get_db)):
    """Get latest run summary for each known agent.

    Returns one entry per agent with their most recent run stats.
    Used by the /transparencia page to show live agent status.
    """
    agent_names = (
        db.query(distinct(AgentRun.agent_name))
        .order_by(AgentRun.agent_name)
        .all()
    )
    summaries = []
    for (name,) in agent_names:
        latest = (
            db.query(AgentRun)
            .filter(AgentRun.agent_name == name)
            .order_by(desc(AgentRun.started_at))
            .first()
        )
        if latest:
            total_sources = 0
            if latest.data_sources and isinstance(latest.data_sources, dict):
                total_sources = len(latest.data_sources)

            summaries.append({
                "agent_name": name,
                "last_run": latest.started_at.isoformat() if latest.started_at else None,
                "status": latest.status,
                "items_processed": latest.items_processed or 0,
                "avg_confidence": latest.avg_confidence,
                "sources": total_sources,
                "error_count": latest.error_count,
            })

    return summaries


@router.post("/runs/{agent_name}/trigger")
def trigger_agent(agent_name: str):
    """Trigger a manual agent run.

    This is a placeholder — in production, this would enqueue
    the agent run via a task queue (Celery, Redis Streams, etc.).
    """
    valid_agents = ["sintese", "radar", "codigo", "funding", "mercado"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent '{agent_name}'. Valid: {valid_agents}",
        )

    return {
        "message": f"Agent '{agent_name}' run triggered",
        "status": "queued",
        "note": "Manual trigger is a placeholder — production will use a task queue",
    }
