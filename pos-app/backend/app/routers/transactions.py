"""API-06 POST /transactions。"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_session
from ..models import Staff
from ..schemas import CommitRequest, CommitResponse
from ..security import get_current_staff
from ..services.pricing_service import PricingService
from ..services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", response_model=CommitResponse, status_code=status.HTTP_201_CREATED)
def commit(
    body: CommitRequest,
    session: Session = Depends(get_session),
    clock: Clock = Depends(get_clock),
    staff: Staff = Depends(get_current_staff),
):
    return TransactionService(session, PricingService(session, clock)).commit(body, staff)
