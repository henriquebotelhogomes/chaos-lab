from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class Product(BaseModel):
    id: str = Field(..., description="Unique product SKU ID")
    name: str = Field(..., description="Product commercial name")
    category: str = Field(..., description="Department category")
    price_cents: int = Field(..., ge=0, description="Price in cents (e.g. 9900 = $99.00)")
    stock_quantity: int = Field(..., ge=0, description="Available stock units")


class CartItem(BaseModel):
    product_id: str
    quantity: int = Field(..., ge=1, le=100)


class CheckoutRequest(BaseModel):
    customer_id: str = Field(..., description="Customer identifier")
    payment_method: str = Field(default="credit_card", description="credit_card, pix, boleto")
    items: list[CartItem] = Field(..., min_length=1)
    shipping_address: str = Field(..., description="Target delivery address")


class Order(BaseModel):
    order_id: str
    customer_id: str
    status: OrderStatus
    items: list[CartItem]
    total_amount_cents: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_detail: str | None = None
