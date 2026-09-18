"""API-03 GET /products/{code}。"""
from fastapi import APIRouter, Depends, Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_session
from ..errors import ProductNotFound
from ..models import Product
from ..schemas import PRODUCT_CODE_PATTERN, ProductInfo
from ..security import get_current_staff

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(get_current_staff)])


@router.get("/{code}", response_model=ProductInfo)
def get_product(code: str = Path(pattern=PRODUCT_CODE_PATTERN), session: Session = Depends(get_session)):
    p = session.execute(select(Product).where(Product.product_code == code)).scalar_one_or_none()
    if p is None:
        raise ProductNotFound(details={"product_code": code})
    return ProductInfo.model_validate(p, from_attributes=True)
