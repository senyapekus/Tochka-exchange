from datetime import datetime
from typing import List, Union, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models.users import User_db
from app.db_models.limit_orders import LimitOrder_db
from app.db_models.market_orders import MarketOrder_db
from app.db_models.orderbook import OrderBook_db
from app.db_models.transactions import Transaction_db
from app.db_models.balances import Balance_db
from app.models import LimitOrderBody, LimitOrder, MarketOrder, MarketOrderBody, CreateOrderResponse, Direction, \
    OrderStatus, Ok
from app.db_session_provider import get_db
from uuid import uuid4, UUID
from app.dependencies import get_api_key, get_user
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import cast, String
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError

router = APIRouter(prefix="/api/v1/order", tags=["order"])


@router.post("", responses={200: {"model": CreateOrderResponse}})
async def create_order(
        order_body: LimitOrderBody | MarketOrderBody,
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    async with db.begin():
        try:
            user = await get_user(api_key, db)

            await _check_and_reserve_funds(
                db=db,
                user_id=user.id,
                ticker=order_body.ticker,
                direction=order_body.direction,
                qty=order_body.qty,
                price=order_body.price if isinstance(order_body, LimitOrderBody) else None
            )

            order = await _create_order_record(db, user, order_body)

            orderbook = await _get_or_create_orderbook(db, order_body.ticker)

            await _execute_order(db, order, orderbook, order_body)

            return CreateOrderResponse(success=True, order_id=order.id)

        except Exception as e:
            await db.rollback()
            raise _handle_error(e)


@router.get("", responses={200: {"model": List[Union[LimitOrder, MarketOrder]]}})
async def list_orders(
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.api_key == api_key)
    )

    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit_orders_result = await db.execute(
        select(LimitOrder_db).where(
            (LimitOrder_db.user_id == user.id) &
            (cast(LimitOrder_db.status, String) != "CANCELLED")
        )
    )
    limit_orders = limit_orders_result.scalars().all()

    market_orders_result = await db.execute(
        select(MarketOrder_db).where(
            (MarketOrder_db.user_id == user.id) &
            (cast(MarketOrder_db.status, String) != "CANCELLED")
        )
    )
    market_orders = market_orders_result.scalars().all()

    orders = []
    for order in limit_orders:
        orders.append(LimitOrder(
            id=order.id,
            status=OrderStatus(order.status),
            user_id=order.user_id,
            timestamp=order.timestamp.isoformat() + "Z",
            body=LimitOrderBody(
                direction=Direction(order.direction),
                ticker=order.ticker,
                qty=order.qty,
                price=order.price
            ),
            filled=order.filled
        ))

    for order in market_orders:
        orders.append(MarketOrder(
            id=order.id,
            status=OrderStatus(order.status),
            user_id=order.user_id,
            timestamp=order.timestamp.isoformat() + "Z",
            body=MarketOrderBody(
                direction=Direction(order.direction),
                ticker=order.ticker,
                qty=order.qty
            )
        ))

    return orders


@router.get("/{order_id}", responses={200: {"model": Union[LimitOrder, MarketOrder]}})
async def get_order(
        order_id: UUID,
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.api_key == api_key)
    )

    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit_order_result = await db.execute(
        select(LimitOrder_db).where(LimitOrder_db.id == order_id)
    )
    limit_order = limit_order_result.scalar_one_or_none()

    market_order_result = await db.execute(
        select(MarketOrder_db).where(MarketOrder_db.id == order_id)
    )
    market_order = market_order_result.scalar_one_or_none()

    if limit_order:
        if limit_order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return LimitOrder(
            id=limit_order.id,
            status=OrderStatus(limit_order.status),
            user_id=limit_order.user_id,
            timestamp=limit_order.timestamp.isoformat() + "Z",
            body=LimitOrderBody(
                direction=Direction(limit_order.direction),
                ticker=limit_order.ticker,
                qty=limit_order.qty,
                price=limit_order.price
            ),
            filled=limit_order.filled
        )
    elif market_order:
        if market_order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        return MarketOrder(
            id=market_order.id,
            status=OrderStatus(market_order.status),
            user_id=market_order.user_id,
            timestamp=market_order.timestamp.isoformat() + "Z",
            body=MarketOrderBody(
                direction=Direction(market_order.direction),
                ticker=market_order.ticker,
                qty=market_order.qty
            )
        )
    else:
        raise HTTPException(status_code=404, detail="Order not found")


@router.delete("/{order_id}", responses={200: {"model": Ok}})
async def cancel_order(
        order_id: UUID,
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    user_result = await db.execute(
        select(User_db).where(User_db.api_key == api_key)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    limit_order_result = await db.execute(
        select(LimitOrder_db).where(LimitOrder_db.id == order_id)
    )
    order = limit_order_result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Limit order not found (cannot cancel market orders)")

    if order.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if order.status not in [OrderStatus.NEW, OrderStatus.PARTIALLY_EXECUTED]:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled")

    unfilled_qty = order.qty - order.filled
    if unfilled_qty <= 0:
        raise HTTPException(status_code=400, detail="Order already fully executed")

    if order.direction == "BUY":
        refund_amount = unfilled_qty * order.price
        balance = await _get_balance(db, user.id, "RUB")
        balance.amount += refund_amount
    else:
        balance = await _get_balance(db, user.id, order.ticker)
        balance.amount += unfilled_qty

    db.add(balance)

    orderbook_result = await db.execute(
        select(OrderBook_db).where(OrderBook_db.ticker == order.ticker)
    )
    orderbook = orderbook_result.scalar_one_or_none()

    if orderbook:
        levels = orderbook.bid_levels if order.direction == "BUY" else orderbook.ask_levels
        for level in levels:
            if level["price"] == order.price:
                level["qty"] -= unfilled_qty
                break

        levels[:] = [lvl for lvl in levels if lvl["qty"] > 0]

        if order.direction == "BUY":
            orderbook.bid_levels = sorted(levels, key=lambda x: -x["price"])
            flag_modified(orderbook, "bid_levels")
        else:
            orderbook.ask_levels = sorted(levels, key=lambda x: x["price"])
            flag_modified(orderbook, "ask_levels")

    order.status = OrderStatus.CANCELLED
    db.add(order)

    await db.commit()

    return Ok()


async def _create_order_record(
        db: AsyncSession,
        user: User_db,
        order_body: LimitOrderBody | MarketOrderBody
) -> Union[LimitOrder_db, MarketOrder_db]:
    order_id = uuid4()

    if isinstance(order_body, LimitOrderBody):
        order = LimitOrder_db(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=user.id,
            timestamp=datetime.utcnow(),
            direction=order_body.direction,
            ticker=order_body.ticker,
            qty=order_body.qty,
            price=order_body.price,
            filled=0
        )
    else:
        order = MarketOrder_db(
            id=order_id,
            status=OrderStatus.NEW,
            user_id=user.id,
            timestamp=datetime.utcnow(),
            direction=order_body.direction,
            ticker=order_body.ticker,
            qty=order_body.qty
        )

    db.add(order)
    await db.flush()

    return order


async def _get_or_create_orderbook(
        db: AsyncSession,
        ticker: str
) -> OrderBook_db:
    orderbook = await db.execute(
        select(OrderBook_db)
        .where(OrderBook_db.ticker == ticker)
    )
    result_orderbook = orderbook.scalar_one_or_none()

    if not result_orderbook:
        result_orderbook = OrderBook_db(
            ticker=ticker,
            bid_levels=[],
            ask_levels=[]
        )
        db.add(result_orderbook)
        await db.flush()

    return result_orderbook


async def _execute_order(
        db: AsyncSession,
        order: Union[LimitOrder_db, MarketOrder_db],
        orderbook: OrderBook_db,
        order_body: LimitOrderBody | MarketOrderBody
):
    if isinstance(order_body, MarketOrderBody):
        await _execute_market_order(db, order, orderbook)
    else:
        await _execute_limit_order(db, order, orderbook, order_body)


async def _execute_market_order(
        db: AsyncSession,
        order: MarketOrder_db,
        orderbook: OrderBook_db
):
    is_buy = order.direction == "BUY"
    levels = orderbook.ask_levels if is_buy else orderbook.bid_levels

    total_available_qty = sum(level["qty"] for level in levels)
    if total_available_qty < order.qty:
        order.filled = 0
        order.status = OrderStatus.NEW
        return

    remaining_qty = order.qty
    executed_levels = []
    executed_qty = 0

    for level in levels:
        if remaining_qty <= 0:
            break

        price = level["price"]
        trade_qty = min(level["qty"], remaining_qty)
        remaining_qty -= trade_qty
        executed_qty += trade_qty

        buyer_id = order.user_id if is_buy else UUID(level["user_id"])
        seller_id = UUID(level["user_id"]) if is_buy else order.user_id

        await _create_transaction(
            db=db,
            ticker=order.ticker,
            amount=trade_qty,
            price=price,
            buyer_id=buyer_id,
            seller_id=seller_id
        )

        if is_buy:
            level["reserved_funds"] -= trade_qty * price
        else:
            level["reserved_funds"] -= trade_qty
        level["reserved_funds"] = max(level["reserved_funds"], 0)

        level["qty"] -= trade_qty

        if "order_id" in level:
            matched_order_id = UUID(level["order_id"])
            matched_order = await db.get(LimitOrder_db, matched_order_id)
            if matched_order:
                matched_order.filled += trade_qty
                if matched_order.filled >= matched_order.qty:
                    matched_order.status = OrderStatus.EXECUTED
                else:
                    matched_order.status = OrderStatus.PARTIALLY_EXECUTED
                db.add(matched_order)

        if level["qty"] <= 0:
            executed_levels.append(level)

    for level in executed_levels:
        levels.remove(level)

    if is_buy:
        orderbook.ask_levels = levels
        flag_modified(orderbook, "ask_levels")
    else:
        orderbook.bid_levels = levels
        flag_modified(orderbook, "bid_levels")

    order.filled = executed_qty
    order.status = OrderStatus.EXECUTED


async def _execute_limit_order(
        db: AsyncSession,
        order: LimitOrder_db,
        orderbook: OrderBook_db,
        order_body: LimitOrderBody
):
    levels = orderbook.ask_levels if order.direction == "BUY" else orderbook.bid_levels
    is_buy = order.direction == "BUY"

    matched_qty = 0
    remaining_qty = order.qty
    executed_levels = []

    for level in levels:
        if remaining_qty <= 0:
            break

        level_price = level["price"]
        if (is_buy and level_price > order.price) or (not is_buy and level_price < order.price):
            break

        trade_qty = min(remaining_qty, level["qty"])
        remaining_qty -= trade_qty
        matched_qty += trade_qty

        buyer_id = order.user_id if is_buy else UUID(level["user_id"])
        seller_id = UUID(level["user_id"]) if is_buy else order.user_id

        await _create_transaction(
            db=db,
            ticker=order.ticker,
            amount=trade_qty,
            price=level_price,
            buyer_id=buyer_id,
            seller_id=seller_id
        )

        if is_buy:
            level["reserved_funds"] -= trade_qty
        else:
            level["reserved_funds"] -= trade_qty * level_price
        level["reserved_funds"] = max(level["reserved_funds"], 0)

        level["qty"] -= trade_qty
        if level["qty"] <= 0:
            executed_levels.append(level)

            if "order_id" in level:
                matched_order_id = UUID(level["order_id"])
                matched_order = await db.get(LimitOrder_db, matched_order_id)
                if matched_order:
                    matched_order.filled = matched_order.qty
                    matched_order.status = OrderStatus.EXECUTED
                    db.add(matched_order)
        else:
            if "order_id" in level:
                matched_order_id = UUID(level["order_id"])
                matched_order = await db.get(LimitOrder_db, matched_order_id)
                if matched_order:
                    matched_order.filled += trade_qty
                    matched_order.status = OrderStatus.PARTIALLY_EXECUTED
                    db.add(matched_order)

    for lvl in executed_levels:
        levels.remove(lvl)

    if is_buy:
        orderbook.ask_levels = levels
        flag_modified(orderbook, "ask_levels")
    else:
        orderbook.bid_levels = levels
        flag_modified(orderbook, "bid_levels")

    order.filled = matched_qty

    if matched_qty == 0:
        order.status = OrderStatus.NEW
        await _add_to_orderbook(orderbook, order_body, 0, order.user_id, order.id)
    elif remaining_qty == 0:
        order.status = OrderStatus.EXECUTED
    else:
        order.status = OrderStatus.PARTIALLY_EXECUTED
        await _add_to_orderbook(orderbook, order_body, matched_qty, order.user_id, order.id)


async def _create_transaction(
        db: AsyncSession,
        ticker: str,
        amount: int,
        price: int,
        buyer_id: UUID,
        seller_id: UUID
):
    transaction = Transaction_db(
        ticker=ticker,
        amount=amount,
        price=price,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)

    total_cost = amount * price

    buyer_rub_balance = await _get_balance(db, buyer_id, "RUB")
    buyer_rub_balance.amount -= total_cost
    db.add(buyer_rub_balance)

    await _update_balance(db, buyer_id, ticker, amount)

    seller_asset_balance = await _get_balance(db, seller_id, ticker)
    seller_asset_balance.amount -= amount
    db.add(seller_asset_balance)

    await _update_balance(db, seller_id, "RUB", total_cost)


def _merge_level(levels: list[dict], new_level: dict):
    for level in levels:
        if (
                level["price"] == new_level["price"] and
                level.get("user_id") == new_level.get("user_id") and
                level.get("order_id") == new_level.get("order_id")
        ):
            level["qty"] += new_level["qty"]
            for key in ["reserved_rub", "reserved_funds"]:
                if key in new_level:
                    level[key] = level.get(key, 0) + new_level.get(key, 0)
            return

    levels.append(new_level)


async def _add_to_orderbook(
        orderbook: OrderBook_db,
        order_body: LimitOrderBody,
        executed_qty: int,
        user_id: UUID,
        order_id: UUID
):
    qty_left = order_body.qty - executed_qty
    if qty_left <= 0:
        return

    reserved_funds = qty_left * order_body.price if order_body.direction == "BUY" else qty_left

    new_level = {
        "price": order_body.price,
        "qty": qty_left,
        "user_id": str(user_id),
        "order_id": str(order_id),
        "reserved_funds": reserved_funds
    }

    levels = orderbook.bid_levels if order_body.direction == "BUY" else orderbook.ask_levels

    _merge_level(levels, new_level)
    if order_body.direction == "BUY":
        orderbook.bid_levels = sorted(levels, key=lambda x: -x["price"])
        flag_modified(orderbook, "bid_levels")
    else:
        orderbook.ask_levels = sorted(levels, key=lambda x: x["price"])
        flag_modified(orderbook, "ask_levels")


async def _get_balance(db: AsyncSession, user_id: UUID, ticker: str) -> Balance_db:
    result = await db.execute(
        select(Balance_db).where(Balance_db.user_id == user_id, Balance_db.ticker == ticker)
    )
    balance = result.scalar_one_or_none()
    if balance is None:
        balance = Balance_db(user_id=user_id, ticker=ticker, amount=0)
        db.add(balance)

    await db.flush()

    return balance


async def _update_balance(db: AsyncSession, user_id: UUID, ticker: str, delta: int):
    balance = await _get_balance(db, user_id, ticker)

    new_amount = balance.amount + delta
    if new_amount < 0:
        raise HTTPException(status_code=400, detail=f"Insufficient balance for {ticker}")
    balance.amount = new_amount

    db.add(balance)


async def _check_and_reserve_funds(
        db: AsyncSession,
        user_id: UUID,
        ticker: str,
        direction: str,
        qty: int,
        price: Optional[int] = None
):
    if direction == "SELL":
        balance = await _get_balance(db, user_id, ticker)
        if balance.amount < qty:
            raise HTTPException(status_code=400, detail="Insufficient balance for SELL order")

    elif direction == "BUY":
        if price is None:
            return

        rub_balance = await _get_balance(db, user_id, "RUB")
        total_cost = qty * price
        if rub_balance.amount < total_cost:
            raise HTTPException(status_code=400, detail="Insufficient RUB balance for BUY order")


async def _refund_unused_funds(
        db: AsyncSession,
        user_id: UUID,
        ticker: str,
        direction: str,
        qty: int,
        filled: Optional[int],
        price: Optional[int] = None
):
    unfilled_qty = qty - (filled or 0)

    if unfilled_qty <= 0 or price is None:
        return

    if direction == "BUY" and price is not None:
        refund_amount = unfilled_qty * price
        rub_balance = await _get_balance(db, user_id, "RUB")
        rub_balance.amount += refund_amount

        db.add(rub_balance)

    elif direction == "SELL":
        asset_balance = await _get_balance(db, user_id, ticker)
        asset_balance.amount += unfilled_qty

        db.add(asset_balance)


def _handle_error(e: Exception) -> HTTPException:
    if isinstance(e, IntegrityError):
        return HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    elif isinstance(e, HTTPException):
        return e
    elif isinstance(e, DBAPIError):
        return HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    else:
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
