"""
주식 손익 계산 서비스
- 종목별 요약 (총매수, 총매도, 실현손익, 보유수량, 평균매수단가)
- 전체 포트폴리오 요약
- 평균단가법(이동평균법) 사용
"""
from sqlalchemy import func

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
            total_buy += trade.total_amount
            total_cost += trade.total_amount
            holdings += trade.quantity
        elif trade.type == "sell":
            total_sell += trade.total_amount

            # 평균단가법: 매도 시 실현손익 계산
            if holdings > 0:
                avg_cost = total_cost / holdings
                cost_of_sold = int(avg_cost * trade.quantity)
                realized_pnl += trade.total_amount - cost_of_sold
                total_cost -= cost_of_sold
                holdings -= trade.quantity

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
