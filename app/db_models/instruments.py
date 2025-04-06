from sqlalchemy import Column, UUID, String, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from db_session_provider import Base

class Instrument_db(Base):
    __tablename__ = "instruments"
    name = Column(String(255), nullable=False)
    ticker = Column(String(10), primary_key=True)
    