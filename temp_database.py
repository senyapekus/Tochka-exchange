from typing import Dict, List
from models import User, Instrument, L2OrderBook, Transaction, Level

users_db: Dict[int, User] = {}

instruments_db: List[Instrument] = [
    Instrument(name="test_1", ticker="TEST1"),
    Instrument(name="test_2", ticker="TEST2"),
]

orderbooks_db: Dict[str, L2OrderBook] = {
    "TEST1": L2OrderBook(
        bid_levels=[Level(price=100, qty=100), Level(price=123, qty=5000)],
        ask_levels=[Level(price=228, qty=2), Level(price=1520, qty=1)],
    ),
    "TEST2": L2OrderBook(
        bid_levels=[Level(price=27900, qty=10), Level(price=27, qty=5)],
        ask_levels=[Level(price=67000, qty=200), Level(price=54535, qty=105)],
    ),
}

transactions_db: Dict[str, List[Transaction]] = {
    "TEST1": [
        Transaction(ticker="TEST1", amount=10, price=150, timestamp="2025-03-08T15:39:09.660Z"),
        Transaction(ticker="TEST1", amount=5, price=149, timestamp="2025-03-09T15:39:09.660Z"),
    ],
    "TEST2": [
        Transaction(ticker="TEST2", amount=2, price=2800, timestamp="2025-02-09T15:39:09.660Z"),
    ],
}

balances_db: Dict[str, Dict[str, int]] = {}

def generate_user_id() -> str:
    return str(max(int(k) for k in users_db.keys()) + 1) if users_db else "1"
