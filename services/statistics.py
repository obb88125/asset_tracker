"""
통계 데이터 생성 서비스
- 대시보드에 필요한 각종 집계/요약 데이터
"""
from collections import defaultdict

from sqlalchemy import case, func

from database import db_session
from models.account import Account
from models.person import Person
from models.transaction import Transaction
from models.stock import StockTrade
from services.stock_calculator import calculate_portfolio


def get_summary_stats() -> dict:
    """
    전체 요약 통계

    Returns:
        {
            total_deposit: int,      # 총 입금
            total_withdrawal: int,   # 총 출금
            net_amount: int,         # 순 금액
            person_count: int,       # 인물 수
            transaction_count: int,  # 거래 건수
            stock_buy_total: int,    # 주식 매수 총액
            stock_sell_total: int,   # 주식 매도 총액
            stock_realized_pnl: int, # 주식 실현 손익
        }
    """
    # 입출금 합계
    deposit_sum = (
        db_session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.type == "deposit")
        .scalar()
    )

    withdrawal_sum = (
        db_session.query(func.coalesce(func.sum(Transaction.amount), 0))
        .filter(Transaction.type == "withdrawal")
        .scalar()
    )

    # 인물 수
    person_count = db_session.query(func.count(Person.id)).scalar()

    # 거래 건수
    transaction_count = db_session.query(func.count(Transaction.id)).scalar()

    # 주식 매매 합계
    stock_buy_total = (
        db_session.query(func.coalesce(func.sum(StockTrade.total_amount), 0))
        .filter(StockTrade.type == "buy")
        .scalar()
    )
    stock_sell_total = (
        db_session.query(func.coalesce(func.sum(StockTrade.total_amount), 0))
        .filter(StockTrade.type == "sell")
        .scalar()
    )

    # 실현 손익 (포트폴리오 계산)
    portfolio = calculate_portfolio()
    stock_realized_pnl = sum(p["realized_pnl"] for p in portfolio)

    return {
        "total_deposit": int(deposit_sum),
        "total_withdrawal": int(withdrawal_sum),
        "net_amount": int(deposit_sum) - int(withdrawal_sum),
        "person_count": person_count,
        "transaction_count": transaction_count,
        "tx_count": transaction_count,
        "stock_buy_total": int(stock_buy_total),
        "stock_sell_total": int(stock_sell_total),
        "stock_realized_pnl": stock_realized_pnl,
        "stock_pnl": stock_realized_pnl,
    }


def get_monthly_flow() -> dict:
    """
    월별 입출금 데이터

    Returns:
        {
            labels: ['2024-01', '2024-02', ...],
            deposits: [금액, ...],
            withdrawals: [금액, ...],
        }
    """
    # 월별 입금/출금 집계
    results = (
        db_session.query(
            func.strftime("%Y-%m", Transaction.transaction_date).label("month"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "deposit", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("deposits"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "withdrawal", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("withdrawals"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )

    labels = []
    deposits = []
    withdrawals = []

    for row in results:
        if row.month:
            labels.append(row.month)
            deposits.append(int(row.deposits))
            withdrawals.append(int(row.withdrawals))

    return {
        "labels": labels,
        "deposits": deposits,
        "withdrawals": withdrawals,
    }


def get_people_share(limit: int = 10) -> list[dict]:
    """
    인물별 거래 비중 (상위 N명)

    Args:
        limit: 반환할 인물 수 (기본 10)

    Returns:
        [{name: str, total_amount: int}, ...]
    """
    results = (
        db_session.query(
            Person.display_name.label("name"),
            func.sum(Transaction.amount).label("total_amount"),
        )
        .join(Transaction, Transaction.person_id == Person.id)
        .group_by(Person.id)
        .order_by(func.sum(Transaction.amount).desc())
        .limit(limit)
        .all()
    )

    return [
        {"name": row.name, "total_amount": int(row.total_amount)}
        for row in results
    ]


def get_cumulative_flow() -> dict:
    """
    일별 누적 순자산 (입금 - 출금)

    Returns:
        {dates: ['2024-01-01', ...], cumulative_amounts: [금액, ...]}
    """
    results = (
        db_session.query(
            func.strftime("%Y-%m-%d", Transaction.transaction_date).label("date"),
            func.sum(
                case(
                    (Transaction.type == "deposit", Transaction.amount),
                    (Transaction.type == "withdrawal", -Transaction.amount),
                    else_=0,
                )
            ).label("net"),
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    dates = []
    cumulative_amounts = []
    cumulative = 0

    for row in results:
        if row.date:
            cumulative += int(row.net)
            dates.append(row.date)
            cumulative_amounts.append(cumulative)

    return {"dates": dates, "cumulative_amounts": cumulative_amounts}


def get_heatmap_data() -> list[dict]:
    """
    일별 거래 건수 (히트맵용)

    Returns:
        [{date: '2024-01-01', count: 5}, ...]
    """
    results = (
        db_session.query(
            func.strftime("%Y-%m-%d", Transaction.transaction_date).label("date"),
            func.count(Transaction.id).label("count"),
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    return [
        {"date": row.date, "count": row.count}
        for row in results
        if row.date
    ]


def get_account_comparison() -> list[dict]:
    """
    계좌별 입금/출금 비교

    Returns:
        [{account_name: str, deposits: int, withdrawals: int}, ...]
    """
    results = (
        db_session.query(
            Account.name.label("account_name"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "deposit", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("deposits"),
            func.coalesce(
                func.sum(
                    case(
                        (Transaction.type == "withdrawal", Transaction.amount),
                        else_=0,
                    )
                ),
                0,
            ).label("withdrawals"),
        )
        .outerjoin(Transaction, Transaction.account_id == Account.id)
        .group_by(Account.id)
        .order_by(Account.name)
        .all()
    )

    return [
        {
            "account_name": row.account_name,
            "deposits": int(row.deposits),
            "withdrawals": int(row.withdrawals),
        }
        for row in results
    ]


def get_asset_timeline() -> dict:
    """
    은행 입출금과 주식 매수/매도를 같은 시간축으로 결합한 추정 자산 흐름.

    현재 시세 데이터가 없으므로 보유 주식은 매입 원가 기준 장부가로 계산한다.
    """
    daily_cash_flow = defaultdict(int)
    daily_stock_cash_flow = defaultdict(int)
    daily_stock_book_value = {}
    daily_realized_pnl = defaultdict(int)
    events = []

    tx_rows = (
        db_session.query(
            func.strftime("%Y-%m-%d", Transaction.transaction_date).label("date"),
            func.sum(
                case(
                    (Transaction.type == "deposit", Transaction.amount),
                    (Transaction.type == "withdrawal", -Transaction.amount),
                    else_=0,
                )
            ).label("net"),
        )
        .group_by("date")
        .all()
    )
    for row in tx_rows:
        if row.date:
            daily_cash_flow[row.date] += int(row.net or 0)

    trades = (
        db_session.query(StockTrade)
        .order_by(StockTrade.trade_date.asc(), StockTrade.id.asc())
        .all()
    )

    positions = defaultdict(lambda: {"quantity": 0, "cost": 0})
    realized_pnl_total = 0

    for trade in trades:
        if not trade.trade_date:
            continue

        date_key = trade.trade_date.strftime("%Y-%m-%d")
        stock_name = trade.stock.name if trade.stock else "알 수 없는 종목"
        fee = trade.fee or 0
        tax = trade.tax or 0
        position = positions[trade.stock_id]

        if trade.type == "buy":
            buy_cost = trade.total_amount + fee
            position["quantity"] += trade.quantity
            position["cost"] += buy_cost
            daily_stock_cash_flow[date_key] -= buy_cost
        elif trade.type == "sell":
            sell_proceeds = trade.total_amount - fee - tax
            daily_stock_cash_flow[date_key] += sell_proceeds

            if position["quantity"] > 0:
                sold_quantity = min(trade.quantity, position["quantity"])
                avg_cost = position["cost"] / position["quantity"]
                cost_of_sold = int(avg_cost * sold_quantity)
                pnl = sell_proceeds - cost_of_sold
                realized_pnl_total += pnl
                daily_realized_pnl[date_key] += pnl
                position["quantity"] -= sold_quantity
                position["cost"] -= cost_of_sold
                if position["quantity"] <= 0:
                    position["quantity"] = 0
                    position["cost"] = 0

        daily_stock_book_value[date_key] = sum(p["cost"] for p in positions.values())
        events.append(
            {
                "date": date_key,
                "type": trade.type,
                "stock_name": stock_name,
                "quantity": trade.quantity,
                "amount": trade.total_amount,
                "fee": fee,
                "tax": tax,
            }
        )

    all_dates = sorted(
        set(daily_cash_flow.keys())
        | set(daily_stock_cash_flow.keys())
        | set(daily_stock_book_value.keys())
    )

    dates = []
    cash_values = []
    stock_book_values = []
    asset_values = []
    daily_flows = []
    realized_values = []

    cash = 0
    stock_book = 0
    realized = 0

    for date_key in all_dates:
        cash += daily_cash_flow[date_key] + daily_stock_cash_flow[date_key]
        if date_key in daily_stock_book_value:
            stock_book = daily_stock_book_value[date_key]
        realized += daily_realized_pnl[date_key]

        dates.append(date_key)
        cash_values.append(int(cash))
        stock_book_values.append(int(stock_book))
        asset_values.append(int(cash + stock_book))
        daily_flows.append(int(daily_cash_flow[date_key]))
        realized_values.append(int(realized))

    return {
        "dates": dates,
        "asset_values": asset_values,
        "cash_values": cash_values,
        "stock_book_values": stock_book_values,
        "daily_flows": daily_flows,
        "realized_pnl_values": realized_values,
        "events": events,
        "latest_asset_value": asset_values[-1] if asset_values else 0,
        "latest_cash_value": cash_values[-1] if cash_values else 0,
        "latest_stock_book_value": stock_book_values[-1] if stock_book_values else 0,
        "latest_realized_pnl": realized_pnl_total,
    }
