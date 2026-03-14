from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/movements", tags=["Движения"])


@router.get("/", response_model=List[schemas.MovementOut])
def list_movements(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    product_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    movements = crud.get_movements(
        db, skip=skip, limit=limit,
        product_id=product_id,
        movement_type=movement_type,
        date_from=date_from,
        date_to=date_to,
    )
    result = []
    for m in movements:
        item = schemas.MovementOut.model_validate(m)
        item.product_name = m.product.name if m.product else None
        item.product_sku = m.product.sku if m.product else None
        result.append(item)
    return result


@router.get("/{movement_id}", response_model=schemas.MovementOut)
def get_movement(movement_id: int, db: Session = Depends(get_db)):
    m = crud.get_movement(db, movement_id)
    if not m:
        raise HTTPException(status_code=404, detail="Движение не найдено")
    item = schemas.MovementOut.model_validate(m)
    item.product_name = m.product.name if m.product else None
    item.product_sku = m.product.sku if m.product else None
    return item


@router.post("/", response_model=schemas.MovementOut, status_code=201)
def create_movement(data: schemas.MovementCreate, db: Session = Depends(get_db)):
    movement, error = crud.create_movement(db, data)
    if error:
        raise HTTPException(status_code=422, detail=error)
    item = schemas.MovementOut.model_validate(movement)
    item.product_name = movement.product.name if movement.product else None
    item.product_sku = movement.product.sku if movement.product else None
    return item
