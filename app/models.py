import datetime
from pydantic import BaseModel
from typing import List
from enum import Enum
from uuid import UUID


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"


class NewUser(BaseModel):
    name: str


class User(BaseModel):
    id: UUID
    name: str
    role: UserRole = UserRole.USER
    api_key: str


class Instrument(BaseModel):
    name: str
    ticker: str


class Level(BaseModel):
    price: int
    qty: int


class L2OrderBook(BaseModel):
    bid_levels: List[Level]
    ask_levels: List[Level]


class Transaction(BaseModel):
    ticker: str
    amount: int
    price: int
    timestamp: str


class Body_deposit_api_v1_balance_deposit_post(BaseModel):
    user_id: UUID
    ticker: str
    amount: int


class Body_withdraw_api_v1_balance_withdraw_post(BaseModel):
    user_id: UUID
    ticker: str
    amount: int


class Ok(BaseModel):
    success: bool = True


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    NEW = "NEW"
    EXECUTED = "EXECUTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    CANCELLED = "CANCELLED"


class LimitOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int
    price: int


class MarketOrderBody(BaseModel):
    direction: Direction
    ticker: str
    qty: int


class LimitOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: str
    body: LimitOrderBody
    filled: int = 0


class MarketOrder(BaseModel):
    id: UUID
    status: OrderStatus
    user_id: UUID
    timestamp: str
    body: MarketOrderBody


class CreateOrderResponse(BaseModel):
    success: bool = True
    order_id: UUID
