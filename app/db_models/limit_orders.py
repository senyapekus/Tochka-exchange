import datetime
from sqlalchemy import Column, UUID, DateTime, String, Enum, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.sql import func
from db_session_provider import Base

class LimitOrder_db(Base):
    __tablename__ = "limit_orders"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    status = Column(SQLEnum("NEW", "EXECUTED", "PARTIALLY_EXECUTED", "CANCELLED", name="order_status"), nullable=False)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    price = Column(Integer, nullable=False)
    direction = Column(SQLEnum("BUY", "SELL", name="order_direction"), nullable=False)
    ticker = Column(String(10), ForeignKey("instruments.ticker"), nullable=False)
    qty = Column(Integer, nullable=False)
    filled = Column(Integer, nullable=False, default=0)
