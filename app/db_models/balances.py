from sqlalchemy import Column, UUID, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db_session_provider import Base


class Balance_db(Base):
    __tablename__ = "balances"
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    ticker = Column(String(10), primary_key=True)
    amount = Column(Integer, nullable=False, default=0)
