from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.cost_guard import get_budget_ledger
from app.core.security import get_current_admin
from app.core.vector_store import get_vector_store
from app.models.guardrail_schemas import SpendDashboardResponse, UserSpendSummary

router = APIRouter(prefix="/api/v1/admin", tags=["Admin - Spend Dashboard"], dependencies=[Depends(get_current_admin)])


@router.get("/spend-dashboard", response_model=SpendDashboardResponse)
async def spend_dashboard(request: Request) -> SpendDashboardResponse:
    ledger = get_budget_ledger(request)
    vector_store = get_vector_store(request)

    snapshot = await ledger.dashboard_snapshot()
    users = [UserSpendSummary(**row) for row in snapshot]

    return SpendDashboardResponse(
        users=users,
        total_users=len(users),
        total_spend_usd=round(sum(u.total_spent_usd for u in users), 6),
        total_requests=sum(u.request_count for u in users),
        total_token_burn_blocks=sum(u.blocked_token_burn_count for u in users),
        total_budget_blocks=sum(u.blocked_budget_count for u in users),
        total_rate_limit_blocks=sum(u.blocked_rate_limit_count for u in users),
        policy_index_stats=vector_store.stats(),
        active_threshold=request.app.state.faiss_threshold,
    )
