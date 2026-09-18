"""API-05 POST /pricing/quote。"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_session
from ..schemas import QuoteRequest, QuoteResult
from ..security import get_current_staff
from ..services.pricing_service import PricingService

router = APIRouter(prefix="/pricing", tags=["pricing"], dependencies=[Depends(get_current_staff)])


@router.post("/quote", response_model=QuoteResult)
def quote(body: QuoteRequest, session: Session = Depends(get_session), clock: Clock = Depends(get_clock)):
    svc = PricingService(session, clock)
    return svc.quote(body.member_code, [(i.product_code, i.quantity) for i in body.items], svc.new_context())
