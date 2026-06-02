from flask import jsonify, request
from routes import accounts_bp
from database import db_session
from models.account import Account
from models.transaction import Transaction
from sqlalchemy import func

@accounts_bp.route('/', methods=['GET'])
def get_accounts():
    try:
        accounts = db_session.query(Account).all()
        data = []
        for a in accounts:
            deposits = db_session.query(func.sum(Transaction.amount)).filter(Transaction.account_id == a.id, Transaction.type == 'deposit').scalar() or 0
            withdrawals = db_session.query(func.sum(Transaction.amount)).filter(Transaction.account_id == a.id, Transaction.type == 'withdrawal').scalar() or 0
            tx_count = db_session.query(Transaction).filter(Transaction.account_id == a.id).count()
            
            data.append({
                "id": a.id,
                "name": a.name,
                "institution": a.institution,
                "account_number": a.account_number,
                "total_deposit": deposits,
                "total_withdrawal": withdrawals,
                "tx_count": tx_count
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@accounts_bp.route('/', methods=['POST'])
def add_account():
    try:
        req = request.json
        a = Account(
            name=req.get('name'),
            institution=req.get('institution'),
            account_number=req.get('account_number')
        )
        db_session.add(a)
        db_session.commit()
        return jsonify({"success": True, "data": {"id": a.id}})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})

@accounts_bp.route('/<int:id>', methods=['PUT'])
def update_account(id):
    try:
        req = request.json
        a = db_session.query(Account).get(id)
        if a:
            if 'name' in req: a.name = req['name']
            if 'institution' in req: a.institution = req['institution']
            if 'account_number' in req: a.account_number = req['account_number']
            db_session.commit()
            return jsonify({"success": True, "data": {}})
        return jsonify({"success": False, "error": "Not found"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})

@accounts_bp.route('/<int:id>', methods=['DELETE'])
def delete_account(id):
    try:
        a = db_session.query(Account).get(id)
        if a:
            db_session.delete(a)
            db_session.commit()
        return jsonify({"success": True, "data": {}})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
