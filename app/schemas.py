from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator


# ─── Product ────────────────────────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=100)
    category: Optional[str] = Field(None, max_length=100)
    unit: str = Field(default="шт", max_length=50)
    price: Decimal = Field(default=Decimal("0"), ge=0)
    description: Optional[str] = None
    min_stock: Decimal = Field(default=Decimal("0"), ge=0)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = Field(None, max_length=100)
    unit: Optional[str] = Field(None, max_length=50)
    price: Optional[Decimal] = Field(None, ge=0)
    description: Optional[str] = None
    min_stock: Optional[Decimal] = Field(None, ge=0)


class ProductOut(ProductBase):
    id: int
    current_stock: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ─── StockMovement ───────────────────────────────────────────────────────────

MovementType = Literal["IN", "OUT", "TRANSFER", "INVENTORY"]

MOVEMENT_TYPE_LABELS = {
    "IN": "Приход",
    "OUT": "Расход",
    "TRANSFER": "Перемещение",
    "INVENTORY": "Инвентаризация",
}


class MovementCreate(BaseModel):
    product_id: int
    movement_type: MovementType
    quantity: Decimal = Field(..., gt=0)
    comment: Optional[str] = None


class MovementOut(BaseModel):
    id: int
    product_id: int
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    movement_type: MovementType
    quantity: Decimal
    quantity_before: Decimal
    quantity_after: Decimal
    comment: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Analytics ───────────────────────────────────────────────────────────────

class WarehouseSummary(BaseModel):
    total_products: int
    total_sku_count: int
    low_stock_count: int
    total_stock_value: Decimal
    movements_today: int
    movements_this_month: int


class LowStockItem(BaseModel):
    id: int
    name: str
    sku: str
    category: Optional[str]
    unit: str
    current_stock: Decimal
    min_stock: Decimal
    deficit: Decimal

    model_config = {"from_attributes": True}


class MovementChartPoint(BaseModel):
    date: str
    in_qty: float
    out_qty: float


class TopProduct(BaseModel):
    id: int
    name: str
    sku: str
    category: Optional[str]
    unit: str
    total_out: float
    total_in: float
