from sqlalchemy import Boolean
from sqlalchemy import Column, UUID, String, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from db_session_provider import Base

class OrderResponse_db(Base):
    __tablename__ = "order_responses"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4())
    success = Column(Boolean, nullable=False, default=True)
    order_id = Column(PG_UUID(as_uuid=True), ForeignKey("limit_orders.id"), nullable=False)
