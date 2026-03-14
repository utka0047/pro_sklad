from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas

router = APIRouter(prefix="/products", tags=["Товары"])


@router.get("/", response_model=List[schemas.ProductOut])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    db: Session = Depends(get_db),
):
    return crud.get_products(db, skip=skip, limit=limit, category=category, low_stock_only=low_stock_only)


@router.get("/categories", response_model=List[str])
def list_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


@router.get("/{product_id}", response_model=schemas.ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@router.post("/", response_model=schemas.ProductOut, status_code=201)
def create_product(data: schemas.ProductCreate, db: Session = Depends(get_db)):
    if crud.get_product_by_sku(db, data.sku):
        raise HTTPException(status_code=409, detail=f"Товар с артикулом '{data.sku}' уже существует")
    return crud.create_product(db, data)


@router.put("/{product_id}", response_model=schemas.ProductOut)
def update_product(product_id: int, data: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = crud.update_product(db, product_id, data)
    if not product:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product


@router.delete("/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_product(db, product_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Товар не найден")
