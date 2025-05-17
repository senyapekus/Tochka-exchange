from sqlalchemy import Column, UUID, String, Enum, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db_session_provider import Base


class Instrument_db(Base):
    __tablename__ = "instruments"
    name = Column(String(255), nullable=False)
    ticker = Column(String(10), primary_key=True)

    __table_args__ = (
        CheckConstraint("ticker ~ '^[A-Z]{2,10}$'", name="ticker_format_check"),
    )
