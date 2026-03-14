from datetime import datetime
from sqlalchemy import Column, Integer, String, Numeric, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    category = Column(String(100), nullable=True)
    unit = Column(String(50), default="шт")
    price = Column(Numeric(10, 2), default=0)
    description = Column(Text, nullable=True)
    min_stock = Column(Numeric(10, 3), default=0)
    current_stock = Column(Numeric(10, 3), default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    movements = relationship("StockMovement", back_populates="product", cascade="all, delete-orphan")


class StockMovement(Base):
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    movement_type = Column(
        String(20),
        nullable=False,
        index=True,
    )
    quantity = Column(Numeric(10, 3), nullable=False)
    quantity_before = Column(Numeric(10, 3), nullable=False)
    quantity_after = Column(Numeric(10, 3), nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    product = relationship("Product", back_populates="movements")

    __table_args__ = (
        CheckConstraint(
            "movement_type IN ('IN', 'OUT', 'TRANSFER', 'INVENTORY')",
            name="ck_movement_type",
        ),
        CheckConstraint("quantity > 0", name="ck_quantity_positive"),
    )
