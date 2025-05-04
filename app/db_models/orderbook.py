from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.sql import func
from app.db_session_provider import Base


class OrderBook_db(Base):
    __tablename__ = "orderbook"
    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), ForeignKey("instruments.ticker"), nullable=False, unique=True)
    bid_levels = Column(JSON, nullable=False)
    ask_levels = Column(JSON, nullable=False)
