from sqlalchemy import Column, UUID, String, Enum, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db_session_provider import Base


class WithdrawRequest_db(Base):
    __tablename__ = "withdraw_requests"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    ticker = Column(String(10), ForeignKey("instruments.ticker"), nullable=False)
    amount = Column(Integer, nullable=False)
