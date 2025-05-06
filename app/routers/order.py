from datetime import datetime
from typing import List, Union
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db_models.users import User_db
from app.db_models.limit_orders import LimitOrder_db
from app.db_models.market_orders import MarketOrder_db
from app.db_models.orderbook import OrderBook_db
from app.db_models.transactions import Transaction_db
from app.models import LimitOrderBody, LimitOrder, MarketOrder, MarketOrderBody, CreateOrderResponse, Direction, \
    OrderStatus, Ok
from app.db_session_provider import get_db
from uuid import uuid4, UUID
from app.dependencies import get_api_key
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import cast, String
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, DBAPIError

router = APIRouter(prefix="/api/v1/order", tags=["order"])


@router.post("/", responses={200: {"model": CreateOrderResponse}})
async def create_order(
        order_body: LimitOrderBody | MarketOrderBody,
        api_key: str = Depends(get_api_key),
        db: AsyncSession = Depends(get_db)
):
    async with db.begin():
        try:
            user = await _get_and_lock_user(db, api_key)

            order = await _create_order_record(db, user, order_body)

            orderbook = await _get_or_create_orderbook(db, order_body.ticker)

            await _execute_order(db, order, orderbook, order_body)

            return CreateOrderResponse(success=True, order_id=order.id)

        except Exception as e:
            await db.rollback()
            raise _handle_error(e)


@router.get("/", responses={200: {"model": List[Union[LimitOrder, MarketOrder]]}})
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
    limit_order = limit_order_result.scalar_one_or_none()

    market_order_result = await db.execute(
        select(MarketOrder_db).where(MarketOrder_db.id == order_id)
    )
    market_order = market_order_result.scalar_one_or_none()

    if limit_order:
        if limit_order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        limit_order.status = "CANCELLED"

    elif market_order:
        if market_order.user_id != user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        market_order.status = "CANCELLED"

    else:
        raise HTTPException(status_code=404, detail="Order not found")

    await db.commit()

    return Ok()


async def _get_and_lock_user(db: AsyncSession, api_key: str) -> User_db:
    user = await db.scalar(
        select(User_db)
        .where(User_db.api_key == api_key)
        .with_for_update()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


async def _create_order_record(
        db: AsyncSession,
        user: User_db,
        order_body: LimitOrderBody | MarketOrderBody
) -> Union[LimitOrder_db, MarketOrder_db]:
    order_id = uuid4()
    if isinstance(order_body, LimitOrderBody):
        order = LimitOrder_db(
            id=order_id,
            status="NEW",
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
            status="NEW",
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
    orderbook = await db.scalar(
        select(OrderBook_db)
        .where(OrderBook_db.ticker == ticker)
        .with_for_update()
    )
    if not orderbook:
        orderbook = OrderBook_db(
            ticker=ticker,
            bid_levels=[],
            ask_levels=[]
        )
        db.add(orderbook)
        await db.flush()

    return orderbook


async def _execute_order(
        db: AsyncSession,
        order: Union[LimitOrder_db, MarketOrder_db],
        orderbook: OrderBook_db,
        order_body: LimitOrderBody | MarketOrderBody
):
    if isinstance(order_body, MarketOrderBody):
        await _execute_market_order(db, order, orderbook, order_body)
    else:
        await _execute_limit_order(db, order, orderbook, order_body)


async def _execute_market_order(
        db: AsyncSession,
        order: MarketOrder_db,
        orderbook: OrderBook_db,
        order_body: MarketOrderBody
):
    opposite_levels = orderbook.ask_levels if order_body.direction == "BUY" else orderbook.bid_levels

    if not opposite_levels:
        return

    best_price = opposite_levels[0]["price"]
    executed_qty = min(order_body.qty, opposite_levels[0]["qty"])

    await _create_transaction(
        db,
        order_body.ticker,
        executed_qty,
        best_price
    )

    opposite_levels[0]["qty"] -= executed_qty
    if opposite_levels[0]["qty"] <= 0:
        opposite_levels.pop(0)

    order.filled = executed_qty
    order.status = "EXECUTED" if executed_qty == order_body.qty else "PARTIALLY_EXECUTED"

    flag_modified(orderbook, "ask_levels" if order_body.direction == "BUY" else "bid_levels")


async def _execute_limit_order(
        db: AsyncSession,
        order: LimitOrder_db,
        orderbook: OrderBook_db,
        order_body: LimitOrderBody
):
    opposite_levels = orderbook.ask_levels if order_body.direction == "BUY" else orderbook.bid_levels
    executed_qty = 0

    for level in list(opposite_levels):
        if ((order_body.direction == "BUY" and order_body.price >= level["price"]) or
                (order_body.direction == "SELL" and order_body.price <= level["price"])):

            qty = min(order_body.qty - executed_qty, level["qty"])

            if qty > 0:
                await _create_transaction(
                    db,
                    order_body.ticker,
                    qty,
                    level["price"]
                )

                level["qty"] -= qty
                if level["qty"] <= 0:
                    opposite_levels.remove(level)

                executed_qty += qty
                order.filled = executed_qty
                order.status = "EXECUTED" if executed_qty == order_body.qty else "PARTIALLY_EXECUTED"

    if order_body.direction == "BUY":
        orderbook.ask_levels = sorted(opposite_levels, key=lambda x: x["price"])
    else:
        orderbook.bid_levels = sorted(opposite_levels, key=lambda x: -x["price"])

    flag_modified(orderbook, "ask_levels" if order_body.direction == "BUY" else "bid_levels")

    if executed_qty < order_body.qty:
        await _add_to_orderbook(orderbook, order_body, executed_qty)


async def _create_transaction(
        db: AsyncSession,
        ticker: str,
        amount: int,
        price: int
):
    transaction = Transaction_db(
        ticker=ticker,
        amount=amount,
        price=price,
        timestamp=datetime.utcnow()
    )
    db.add(transaction)


async def _add_to_orderbook(
        orderbook: OrderBook_db,
        order_body: LimitOrderBody,
        executed_qty: int
):
    levels = orderbook.bid_levels if order_body.direction == "BUY" else orderbook.ask_levels
    levels.append({
        "price": order_body.price,
        "qty": order_body.qty - executed_qty
    })

    if order_body.direction == "BUY":
        orderbook.bid_levels = sorted(levels, key=lambda x: -x["price"])
    else:
        orderbook.ask_levels = sorted(levels, key=lambda x: x["price"])

    flag_modified(orderbook, "bid_levels" if order_body.direction == "BUY" else "ask_levels")


def _handle_error(e: Exception) -> HTTPException:
    if isinstance(e, IntegrityError):
        return HTTPException(status_code=400, detail=f"Database integrity error: {str(e)}")
    elif isinstance(e, DBAPIError):
        return HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    else:
        return HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
