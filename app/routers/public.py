from fastapi import APIRouter, HTTPException, Depends
from app.models import NewUser, User, Instrument, L2OrderBook, Transaction, Level
from app.db_models.users import User_db
from app.db_models.instruments import Instrument_db
from app.db_models.transactions import Transaction_db
from app.db_models.orderbook import OrderBook_db
from app.db_session_provider import get_db
from sqlalchemy import select
from uuid import uuid4
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/public", tags=["public"])


@router.post("/register", responses={200: {"model": User}})
async def register(new_user: NewUser, db: AsyncSession = Depends(get_db)):
    existing_user = await db.execute(select(User_db).where(User_db.name == new_user.name))
    existing_user = existing_user.scalar_one_or_none()

    if existing_user:
        return existing_user

    user_id = uuid4()
    api_key = f"key-{uuid4()}"

    user = User_db(id=user_id, name=new_user.name, role="USER", api_key=api_key)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return user


@router.get("/instrument", responses={200: {"model": List[Instrument]}})
async def list_instruments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Instrument_db))
    instruments = result.scalars().all()

    return instruments


@router.get("/orderbook/{ticker}", responses={200: {"model": L2OrderBook}})
async def get_orderbook(ticker: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    instrument_result = await db.execute(
        select(Instrument_db).where(Instrument_db.ticker == ticker)
    )

    instrument = instrument_result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=422, detail="Instrument not found")

    orderbook_result = await db.execute(
        select(OrderBook_db).where(OrderBook_db.ticker == ticker)
    )

    orderbook = orderbook_result.scalar_one_or_none()
    if not orderbook:
        raise HTTPException(status_code=404, detail="Orderbook not found")

    bid_levels = [
        Level(price=level["price"], qty=level["qty"])
        for level in orderbook.bid_levels[:limit]
    ]
    ask_levels = [
        Level(price=level["price"], qty=level["qty"])
        for level in orderbook.ask_levels[:limit]
    ]

    return L2OrderBook(
        bid_levels=bid_levels,
        ask_levels=ask_levels,
    )


@router.get("/transactions/{ticker}", responses={200: {"model": List[Transaction]}})
async def get_transaction_history(ticker: str, limit: int = 10, db: AsyncSession = Depends(get_db)):
    instrument_result = await db.execute(
        select(Instrument_db).where(Instrument_db.ticker == ticker)
    )

    instrument = instrument_result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=422, detail="Instrument not found")

    transactions_result = await db.execute(
        select(Transaction_db)
        .where(Transaction_db.ticker == ticker)
        .order_by(Transaction_db.timestamp.desc())
        .limit(limit)
    )
    transactions = transactions_result.scalars().all()

    response = [
        Transaction(
            ticker=transaction.ticker,
            amount=transaction.amount,
            price=transaction.price,
            timestamp=transaction.timestamp.isoformat()
        )
        for transaction in transactions
    ]

    return response
