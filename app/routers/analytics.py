from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/analytics", tags=["Аналитика"])


@router.get("/summary", response_model=schemas.WarehouseSummary)
def warehouse_summary(db: Session = Depends(get_db)):
    return crud.get_warehouse_summary(db)


@router.get("/low-stock", response_model=List[schemas.LowStockItem])
def low_stock(db: Session = Depends(get_db)):
    return crud.get_low_stock(db)


@router.get("/movements-chart", response_model=List[schemas.MovementChartPoint])
def movements_chart(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    return crud.get_movements_chart(db, days=days)


@router.get("/top-products", response_model=List[schemas.TopProduct])
def top_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return crud.get_top_products(db, limit=limit)
