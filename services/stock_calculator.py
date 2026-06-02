"""
주식 손익 계산 서비스
- 종목별 요약 (총매수, 총매도, 실현손익, 보유수량, 평균매수단가)
- 전체 포트폴리오 요약
- 평균단가법(이동평균법) 사용
"""
from collections import defaultdict

from database import db_session
from models.stock import Stock, StockTrade


def calculate_stock_summary(stock_id: int) -> dict:
    """
    특정 종목의 손익 요약을 계산 (평균단가법)

    Args:
        stock_id: 종목 ID

    Returns:
        {
            total_buy: int,     # 총 매수 금액
            total_sell: int,    # 총 매도 금액
            realized_pnl: int,  # 실현 손익
            holdings: int,      # 현재 보유 수량
            avg_buy_price: int, # 평균 매수 단가
        }
    """
    trades = (
        db_session.query(StockTrade)
        .filter(StockTrade.stock_id == stock_id)
        .order_by(StockTrade.trade_date.asc())
        .all()
    )

    total_buy = 0
    total_sell = 0
    realized_pnl = 0
    holdings = 0
    total_cost = 0  # 현재 보유분의 총 취득 원가

    for trade in trades:
        if trade.type == "buy":
            buy_cost = trade.total_amount + (trade.fee or 0)
            total_buy += trade.total_amount
            total_cost += buy_cost
            holdings += trade.quantity
        elif trade.type == "sell":
            total_sell += trade.total_amount

            # 평균단가법: 매도 시 실현손익 계산
            if holdings > 0:
                avg_cost = total_cost / holdings
                sold_quantity = min(trade.quantity, holdings)
                cost_of_sold = int(avg_cost * sold_quantity)
                sell_proceeds = trade.total_amount - (trade.fee or 0) - (trade.tax or 0)
                realized_pnl += sell_proceeds - cost_of_sold
                total_cost -= cost_of_sold
                holdings -= sold_quantity

                # 보유수량이 음수가 되지 않도록
                if holdings <= 0:
                    holdings = 0
                    total_cost = 0

    avg_buy_price = int(total_cost / holdings) if holdings > 0 else 0

    return {
        "total_buy": total_buy,
        "total_sell": total_sell,
        "realized_pnl": realized_pnl,
        "holdings": holdings,
        "avg_buy_price": avg_buy_price,
    }


def calculate_portfolio() -> list[dict]:
    """
    전체 포트폴리오 요약

    Returns:
        [
            {
                stock_id: int,
                stock_name: str,
                stock_code: str | None,
                total_buy: int,
                total_sell: int,
                realized_pnl: int,
                holdings: int,
                avg_buy_price: int,
            },
            ...
        ]
    """
    stocks = db_session.query(Stock).all()
    portfolio = []

    for stock in stocks:
        summary = calculate_stock_summary(stock.id)
        portfolio.append(
            {
                "stock_id": stock.id,
                "stock_name": stock.name,
                "stock_code": stock.code,
                **summary,
            }
        )

    # 총 매수 금액 내림차순 정렬
    portfolio.sort(key=lambda x: x["total_buy"], reverse=True)

    return portfolio


def calculate_stock_pnl_timeline(stock_id: int | None = None) -> dict:
    """
    주식 거래내역만으로 계산한 누적 실현손익 타임라인.

    현재 보유 중인 주식의 미실현손익은 시세가 없으므로 포함하지 않는다.
    매도 거래가 발생할 때 평균단가법으로 해당 매도분의 실현손익을 확정한다.
    """
    query = db_session.query(StockTrade).order_by(
        StockTrade.trade_date.asc(),
        StockTrade.id.asc(),
    )
    if stock_id is not None:
        query = query.filter(StockTrade.stock_id == stock_id)

    trades = query.all()
    positions = defaultdict(lambda: {"quantity": 0, "cost": 0})

    total_buy = 0
    total_sell = 0
    total_realized_pnl = 0
    cumulative_pnl = 0
    daily_pnl = defaultdict(int)
    daily_cumulative = {}
    events = []

    for trade in trades:
        if not trade.trade_date:
            continue

        date_key = trade.trade_date.strftime("%Y-%m-%d")
        position = positions[trade.stock_id]
        fee = trade.fee or 0
        tax = trade.tax or 0
        realized_pnl = 0

        if trade.type == "buy":
            buy_cost = trade.total_amount + fee
            total_buy += trade.total_amount
            position["quantity"] += trade.quantity
            position["cost"] += buy_cost
        elif trade.type == "sell":
            total_sell += trade.total_amount
            sell_proceeds = trade.total_amount - fee - tax
            if position["quantity"] > 0:
                sold_quantity = min(trade.quantity, position["quantity"])
                avg_cost = position["cost"] / position["quantity"]
                cost_of_sold = int(avg_cost * sold_quantity)
                realized_pnl = sell_proceeds - cost_of_sold
                total_realized_pnl += realized_pnl
                cumulative_pnl += realized_pnl
                daily_pnl[date_key] += realized_pnl
                position["quantity"] -= sold_quantity
                position["cost"] -= cost_of_sold
                if position["quantity"] <= 0:
                    position["quantity"] = 0
                    position["cost"] = 0

        daily_cumulative[date_key] = cumulative_pnl
        events.append(
            {
                "id": trade.id,
                "date": date_key,
                "stock_id": trade.stock_id,
                "stock_name": trade.stock.name if trade.stock else "알 수 없는 종목",
                "type": trade.type,
                "quantity": trade.quantity,
                "price_per_unit": trade.price_per_unit,
                "total_amount": trade.total_amount,
                "fee": fee,
                "tax": tax,
                "realized_pnl": realized_pnl,
                "cumulative_pnl": cumulative_pnl,
            }
        )

    dates = sorted(daily_cumulative.keys())
    cumulative_values = []
    daily_values = []
    running = 0
    for date_key in dates:
        if date_key in daily_pnl:
            running += daily_pnl[date_key]
        cumulative_values.append(running)
        daily_values.append(daily_pnl[date_key])

    return {
        "dates": dates,
        "cumulative_pnl": cumulative_values,
        "daily_pnl": daily_values,
        "events": events,
        "total_buy": total_buy,
        "total_sell": total_sell,
        "cash_basis_result": total_sell - total_buy,
        "realized_pnl": total_realized_pnl,
        "open_cost_basis": sum(position["cost"] for position in positions.values()),
        "open_quantity": sum(position["quantity"] for position in positions.values()),
    }
