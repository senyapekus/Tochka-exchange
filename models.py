from pydantic import BaseModel
from typing import List
import enum

class UserRole(enum.Enum):
    USER = "USER"
    ADMIN = "ADMIN"

class NewUser(BaseModel):
    name: str

class User(BaseModel):
    id: str
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
    ticker: str
    amount: int

class Body_withdraw_api_v1_balance_withdraw_post(BaseModel):
    ticker: str
    amount: int

class Ok(BaseModel):
    success: bool = True
