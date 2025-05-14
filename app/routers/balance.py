from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.models import Body_deposit_api_v1_balance_deposit_post, Body_withdraw_api_v1_balance_withdraw_post, Ok
from app.db_models.balances import Balance_db
from app.db_models.users import User_db
from typing import Dict
from app.dependencies import check_admin_role, get_api_key
from app.db_session_provider import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

router = APIRouter(prefix="/api/v1/balance", tags=["balance"])
admin_balance_router = APIRouter(prefix="/api/v1/admin/balance", tags=["admin", "balance"])


@router.get("", responses={200: {"model": Dict[str, float]}})
async def get_balances(api_key: str = Depends(get_api_key), db: AsyncSession = Depends(get_db)):
    user_result = await db.execute(
        select(User_db).where(User_db.api_key == api_key)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balances_result = await db.execute(
        select(Balance_db).where(Balance_db.user_id == user.id)
    )
    balances = balances_result.scalars().all()

    return {balance.ticker: balance.amount for balance in balances}


@admin_balance_router.post("/deposit", responses={200: {"model": Ok}})
async def deposit(
        request: Body_deposit_api_v1_balance_deposit_post,
        api_key: str = Depends(get_api_key),
        user: User_db = Depends(check_admin_role),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.id == request.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balance_result = await db.execute(
        select(Balance_db)
        .where(Balance_db.user_id == request.user_id, Balance_db.ticker == request.ticker)
    )
    balance = balance_result.scalar_one_or_none()

    if balance:
        balance.amount += request.amount
    else:
        balance = Balance_db(
            user_id=request.user_id,
            ticker=request.ticker,
            amount=request.amount
        )
        db.add(balance)

    await db.commit()

    return Ok()


@admin_balance_router.post("/withdraw", responses={200: {"model": Ok}})
async def withdraw(
        request: Body_withdraw_api_v1_balance_withdraw_post,
        api_key: str = Depends(get_api_key),
        user: User_db = Depends(check_admin_role),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.id == request.user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    balance_result = await db.execute(
        select(Balance_db)
        .where(Balance_db.user_id == request.user_id, Balance_db.ticker == request.ticker)
    )
    balance = balance_result.scalar_one_or_none()

    if not balance or balance.amount < request.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    balance.amount -= request.amount
    await db.commit()

    return Ok()
