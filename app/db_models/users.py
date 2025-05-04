from sqlalchemy import Column, UUID, String, Enum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.sql import func
from app.db_session_provider import Base


class User_db(Base):
    __tablename__ = "users"
    id = Column(PG_UUID(as_uuid=True), primary_key=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum("USER", "ADMIN", name="user_role"), nullable=False, default="USER")
    api_key = Column(String(255), nullable=False, unique=True)
