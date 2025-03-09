from fastapi import APIRouter, HTTPException
from models import NewUser, User, Instrument, L2OrderBook, Transaction, UserRole
from temp_database import users_db, instruments_db, orderbooks_db, transactions_db, generate_user_id
from uuid import uuid4
from typing import List

router = APIRouter(prefix="/api/v1/public", tags=["public"])

@router.post("/register", response_model=User)
def register(new_user: NewUser):
    user_id = generate_user_id()
    api_key = f"key-{uuid4()}"
    user = User(id=user_id, name=new_user.name, role=UserRole.USER, api_key=api_key)
    users_db[user_id] = user

    return user

@router.get("/instrument", response_model=List[Instrument])
def list_instruments():
    return instruments_db

@router.get("/orderbook/{ticker}", response_model=L2OrderBook)
def get_orderbook(ticker: str, limit: int = 10):
    if ticker not in orderbooks_db:
        raise HTTPException(status_code=422, detail="Instrument not found")
    
    orderbook = orderbooks_db[ticker]

    return L2OrderBook(
        bid_levels=orderbook.bid_levels[:limit],
        ask_levels=orderbook.ask_levels[:limit],
    )

@router.get("/transactions/{ticker}", response_model=List[Transaction])
def get_transaction_history(ticker: str, limit: int = 10):
    if ticker not in transactions_db:
        raise HTTPException(status_code=422, detail="Instrument not found")
    return transactions_db[ticker][:limit]
