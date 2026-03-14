from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session

from app.models import Product, StockMovement
from app.schemas import ProductCreate, ProductUpdate, MovementCreate


# ─── Products ────────────────────────────────────────────────────────────────

def get_products(db: Session, skip: int = 0, limit: int = 200,
                 category: Optional[str] = None, low_stock_only: bool = False):
    q = db.query(Product)
    if category:
        q = q.filter(Product.category == category)
    if low_stock_only:
        q = q.filter(Product.current_stock < Product.min_stock)
    return q.order_by(Product.name).offset(skip).limit(limit).all()


def get_product(db: Session, product_id: int):
    return db.query(Product).filter(Product.id == product_id).first()


def get_product_by_sku(db: Session, sku: str):
    return db.query(Product).filter(Product.sku == sku).first()


def create_product(db: Session, data: ProductCreate):
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, data: ProductUpdate):
    product = get_product(db, product_id)
    if not product:
        return None
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(product, key, value)
    product.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


def delete_product(db: Session, product_id: int):
    product = get_product(db, product_id)
    if not product:
        return False
    db.delete(product)
    db.commit()
    return True


def get_categories(db: Session):
    rows = db.query(Product.category).distinct().filter(Product.category.isnot(None)).all()
    return [r[0] for r in rows]


# ─── Movements ───────────────────────────────────────────────────────────────

def get_movements(db: Session, skip: int = 0, limit: int = 200,
                  product_id: Optional[int] = None,
                  movement_type: Optional[str] = None,
                  date_from: Optional[date] = None,
                  date_to: Optional[date] = None):
    q = db.query(StockMovement).join(Product)
    if product_id:
        q = q.filter(StockMovement.product_id == product_id)
    if movement_type:
        q = q.filter(StockMovement.movement_type == movement_type)
    if date_from:
        q = q.filter(StockMovement.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        q = q.filter(StockMovement.created_at <= datetime.combine(date_to, datetime.max.time()))
    return q.order_by(StockMovement.created_at.desc()).offset(skip).limit(limit).all()


def get_movement(db: Session, movement_id: int):
    return db.query(StockMovement).filter(StockMovement.id == movement_id).first()


def create_movement(db: Session, data: MovementCreate):
    product = get_product(db, data.product_id)
    if not product:
        return None, "Товар не найден"

    qty = Decimal(str(data.quantity))
    qty_before = Decimal(str(product.current_stock))

    if data.movement_type == "IN":
        qty_after = qty_before + qty
    elif data.movement_type == "OUT":
        if qty_before < qty:
            return None, f"Недостаточно товара на складе. Текущий остаток: {qty_before}"
        qty_after = qty_before - qty
    elif data.movement_type == "TRANSFER":
        qty_after = qty_before  # no change in total
    elif data.movement_type == "INVENTORY":
        qty_after = qty  # quantity = new actual count

    movement = StockMovement(
        product_id=data.product_id,
        movement_type=data.movement_type,
        quantity=qty,
        quantity_before=qty_before,
        quantity_after=qty_after,
        comment=data.comment,
    )
    db.add(movement)

    product.current_stock = qty_after
    product.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(movement)
    return movement, None


# ─── Analytics ───────────────────────────────────────────────────────────────

def get_warehouse_summary(db: Session):
    today = date.today()
    month_start = today.replace(day=1)

    total_products = db.query(func.count(Product.id)).scalar()
    total_sku_count = db.query(func.count(Product.id)).filter(Product.current_stock > 0).scalar()
    low_stock_count = db.query(func.count(Product.id)).filter(
        Product.current_stock < Product.min_stock,
        Product.min_stock > 0,
    ).scalar()

    total_value_row = db.query(
        func.sum(Product.current_stock * Product.price)
    ).scalar()
    total_stock_value = Decimal(str(total_value_row or 0))

    movements_today = db.query(func.count(StockMovement.id)).filter(
        cast(StockMovement.created_at, Date) == today
    ).scalar()

    movements_month = db.query(func.count(StockMovement.id)).filter(
        StockMovement.created_at >= datetime.combine(month_start, datetime.min.time())
    ).scalar()

    return {
        "total_products": total_products,
        "total_sku_count": total_sku_count,
        "low_stock_count": low_stock_count,
        "total_stock_value": total_stock_value,
        "movements_today": movements_today,
        "movements_this_month": movements_month,
    }


def get_low_stock(db: Session):
    products = db.query(Product).filter(
        Product.current_stock < Product.min_stock,
        Product.min_stock > 0,
    ).order_by((Product.min_stock - Product.current_stock).desc()).all()

    result = []
    for p in products:
        result.append({
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "category": p.category,
            "unit": p.unit,
            "current_stock": p.current_stock,
            "min_stock": p.min_stock,
            "deficit": p.min_stock - p.current_stock,
        })
    return result


def get_movements_chart(db: Session, days: int = 30):
    date_from = datetime.utcnow() - timedelta(days=days)

    rows = db.query(
        cast(StockMovement.created_at, Date).label("day"),
        StockMovement.movement_type,
        func.sum(StockMovement.quantity).label("total_qty"),
    ).filter(
        StockMovement.created_at >= date_from,
        StockMovement.movement_type.in_(["IN", "OUT"]),
    ).group_by(
        cast(StockMovement.created_at, Date),
        StockMovement.movement_type,
    ).order_by("day").all()

    data: dict[str, dict] = {}
    for row in rows:
        day_str = str(row.day)
        if day_str not in data:
            data[day_str] = {"date": day_str, "in_qty": 0.0, "out_qty": 0.0}
        if row.movement_type == "IN":
            data[day_str]["in_qty"] = float(row.total_qty)
        elif row.movement_type == "OUT":
            data[day_str]["out_qty"] = float(row.total_qty)

    return list(data.values())


def get_top_products(db: Session, limit: int = 10):
    rows = db.query(
        Product.id,
        Product.name,
        Product.sku,
        Product.category,
        Product.unit,
        func.sum(
            func.case((StockMovement.movement_type == "OUT", StockMovement.quantity), else_=0)
        ).label("total_out"),
        func.sum(
            func.case((StockMovement.movement_type == "IN", StockMovement.quantity), else_=0)
        ).label("total_in"),
    ).join(StockMovement, Product.id == StockMovement.product_id, isouter=True
    ).group_by(Product.id, Product.name, Product.sku, Product.category, Product.unit
    ).order_by(func.sum(
        func.case((StockMovement.movement_type == "OUT", StockMovement.quantity), else_=0)
    ).desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "name": r.name,
            "sku": r.sku,
            "category": r.category,
            "unit": r.unit,
            "total_out": float(r.total_out or 0),
            "total_in": float(r.total_in or 0),
        }
        for r in rows
    ]
