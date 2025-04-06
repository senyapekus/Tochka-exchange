from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from db_models.instruments import Instrument_db
from db_models.users import User_db
from models import Instrument as InstrumentSchema, Ok
from db_session_provider import get_db
from dependencies import check_admin_role

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

@router.post("/instrument", response_model=Ok)
async def add_instrument(
    instrument: InstrumentSchema,
    user: User_db = Depends(check_admin_role),
    db: AsyncSession = Depends(get_db)
):
    existing_instrument = await db.execute(
        select(Instrument_db).where(Instrument_db.ticker == instrument.ticker)
    )
    existing_instrument = existing_instrument.scalar_one_or_none()

    if existing_instrument:
        raise HTTPException(status_code=400, detail="Instrument already exists")

    new_instrument = Instrument_db(
        name=instrument.name,
        ticker=instrument.ticker
    )
    db.add(new_instrument)

    await db.commit()

    return Ok()

@router.delete("/instrument/{ticker}", response_model=Ok)
async def delete_instrument(
    ticker: str,
    user: User_db = Depends(check_admin_role),
    db: AsyncSession = Depends(get_db)
):
    existing_instrument = await db.execute(
        select(Instrument_db).where(Instrument_db.ticker == ticker)
    )
    existing_instrument = existing_instrument.scalar_one_or_none()

    if not existing_instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")

    await db.execute(
        delete(Instrument_db).where(Instrument_db.ticker == ticker)
    )

    await db.commit()

    return Ok()
