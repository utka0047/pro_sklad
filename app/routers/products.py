from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
import csv
from io import StringIO
from decimal import Decimal

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


@router.post("/import/csv", status_code=200)
async def import_csv(
    file: UploadFile = File(...),
    on_duplicate: str = Query("skip", regex="^(skip|update|error)$"),
    db: Session = Depends(get_db),
):
    """
    Импорт товаров из CSV файла.
    Ожидаемые колонки: name, sku, category, unit, price, description, min_stock, current_stock
    on_duplicate: skip (не создавать), update (обновить), error (ошибка)
    """
    try:
        content = await file.read()
        text = content.decode('utf-8')
        reader = csv.DictReader(StringIO(text))

        products = []
        for row in reader:
            if not row.get('sku'):
                continue

            try:
                product_data = {
                    'name': row.get('name', '').strip(),
                    'sku': row.get('sku', '').strip(),
                    'category': row.get('category', '').strip() or None,
                    'unit': row.get('unit', 'шт').strip() or 'шт',
                    'price': Decimal(row.get('price', '0')) if row.get('price') else Decimal('0'),
                    'description': row.get('description', '').strip() or None,
                    'min_stock': Decimal(row.get('min_stock', '0')) if row.get('min_stock') else Decimal('0'),
                    'current_stock': Decimal(row.get('current_stock', '0')) if row.get('current_stock') else Decimal('0'),
                }
                products.append(product_data)
            except (ValueError, TypeError) as e:
                pass

        result = crud.bulk_import_products(db, products, on_duplicate=on_duplicate)
        return result

    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="Файл должен быть в кодировке UTF-8")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Ошибка при обработке файла: {str(e)}")
