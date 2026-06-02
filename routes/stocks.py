from flask import jsonify
from routes import stocks_bp
from database import db_session
from models.stock import Stock, StockTrade
from services.stock_calculator import (
    calculate_portfolio,
    calculate_stock_pnl_timeline,
    calculate_stock_summary,
)

@stocks_bp.route('', methods=['GET'])
@stocks_bp.route('/', methods=['GET'])
def get_stocks():
    try:
        portfolio = calculate_portfolio()
        return jsonify({"success": True, "data": portfolio})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@stocks_bp.route('/<int:id>', methods=['GET'])
def get_stock(id):
    try:
        s = db_session.query(Stock).get(id)
        if not s:
            return jsonify({"success": False, "error": "Not found"})
        summary = calculate_stock_summary(id)
        pnl_timeline = calculate_stock_pnl_timeline(id)
        event_by_trade_id = {event["id"]: event for event in pnl_timeline["events"]}
        trades = db_session.query(StockTrade).filter(StockTrade.stock_id == id).order_by(StockTrade.trade_date.desc()).all()
        
        summary["id"] = s.id
        summary["name"] = s.name
        summary["code"] = s.code
        summary["cash_basis_result"] = pnl_timeline["cash_basis_result"]
        summary["open_cost_basis"] = pnl_timeline["open_cost_basis"]
        summary["trades"] = [{
            "id": t.id,
            "date": t.trade_date.isoformat(),
            "type": t.type,
            "quantity": t.quantity,
            "price": t.price_per_unit,
            "total": t.total_amount,
            "fee": t.fee or 0,
            "tax": t.tax or 0,
            "realized_pnl": event_by_trade_id.get(t.id, {}).get("realized_pnl", 0),
        } for t in trades]
        return jsonify({"success": True, "data": summary})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@stocks_bp.route('/<int:id>/timeline', methods=['GET'])
def get_timeline(id):
    try:
        trades = db_session.query(StockTrade).filter(StockTrade.stock_id == id).order_by(StockTrade.trade_date.asc()).all()
        dates = []
        amounts = []
        holdings = []
        current_holding = 0
        for t in trades:
            dates.append(t.trade_date.isoformat())
            amt = t.total_amount if t.type == 'sell' else -t.total_amount
            amounts.append(amt)
            current_holding += t.quantity if t.type == 'buy' else -t.quantity
            holdings.append(current_holding)
            
        return jsonify({"success": True, "data": {"dates": dates, "amounts": amounts, "holdings": holdings}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@stocks_bp.route('/pnl-timeline', methods=['GET'])
def get_pnl_timeline():
    try:
        return jsonify({"success": True, "data": calculate_stock_pnl_timeline()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@stocks_bp.route('/<int:id>/pnl-timeline', methods=['GET'])
def get_stock_pnl_timeline(id):
    try:
        return jsonify({"success": True, "data": calculate_stock_pnl_timeline(id)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@stocks_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    try:
        data = calculate_portfolio()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
