from flask import jsonify
from routes import stocks_bp
from database import db_session
from models.stock import Stock, StockTrade
from services.stock_calculator import calculate_stock_summary, calculate_portfolio

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
        trades = db_session.query(StockTrade).filter(StockTrade.stock_id == id).order_by(StockTrade.trade_date.desc()).all()
        
        summary["id"] = s.id
        summary["name"] = s.name
        summary["code"] = s.code
        summary["trades"] = [{
            "id": t.id,
            "date": t.trade_date.isoformat(),
            "type": t.type,
            "quantity": t.quantity,
            "price": t.price_per_unit,
            "total": t.total_amount
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

@stocks_bp.route('/portfolio', methods=['GET'])
def get_portfolio():
    try:
        data = calculate_portfolio()
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
