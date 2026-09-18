"""API-04 GET /members/{code}（氏名のみ返す）。"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..errors import MemberNotFound
from ..models import Member
from ..schemas import MEMBER_CODE_PATTERN, MemberInfo
from ..security import get_current_staff

router = APIRouter(prefix="/members", tags=["members"], dependencies=[Depends(get_current_staff)])


@router.get("/{code}", response_model=MemberInfo)
def get_member(code: str = Path(pattern=MEMBER_CODE_PATTERN), session: Session = Depends(get_session)):
    m = session.execute(select(Member).where(Member.member_code == code)).scalar_one_or_none()
    if m is None:
        raise MemberNotFound(details={"member_code": code})
    return MemberInfo.model_validate(m, from_attributes=True)
