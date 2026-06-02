from flask import jsonify, request
from routes import people_bp
from database import db_session
from models.person import Person, PersonAlias
from models.transaction import Transaction
from services.person_matcher import merge_persons, split_alias
from sqlalchemy import func

@people_bp.route('/', methods=['GET'])
def get_people():
    try:
        people = db_session.query(Person).all()
        data = []
        for p in people:
            deposits = db_session.query(func.sum(Transaction.amount)).filter(Transaction.person_id == p.id, Transaction.type == 'deposit').scalar() or 0
            withdrawals = db_session.query(func.sum(Transaction.amount)).filter(Transaction.person_id == p.id, Transaction.type == 'withdrawal').scalar() or 0
            data.append({
                "id": p.id,
                "display_name": p.display_name,
                "memo": p.memo,
                "total_deposit": deposits,
                "total_withdrawal": withdrawals,
                "net_amount": deposits - withdrawals,
                "aliases": [a.alias_name for a in p.aliases]
            })
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>', methods=['GET'])
def get_person(id):
    try:
        p = db_session.query(Person).get(id)
        if not p:
            return jsonify({"success": False, "error": "Person not found"})
        deposits = db_session.query(func.sum(Transaction.amount)).filter(Transaction.person_id == p.id, Transaction.type == 'deposit').scalar() or 0
        withdrawals = db_session.query(func.sum(Transaction.amount)).filter(Transaction.person_id == p.id, Transaction.type == 'withdrawal').scalar() or 0
        transactions = db_session.query(Transaction).filter(Transaction.person_id == p.id).order_by(Transaction.transaction_date.desc()).all()
        
        data = {
            "id": p.id,
            "display_name": p.display_name,
            "memo": p.memo,
            "total_deposit": deposits,
            "total_withdrawal": withdrawals,
            "net_amount": deposits - withdrawals,
            "aliases": [{"id": a.id, "name": a.alias_name} for a in p.aliases],
            "transactions": [{
                "id": t.id,
                "date": t.transaction_date.isoformat(),
                "type": t.type,
                "amount": t.amount,
                "description": t.description
            } for t in transactions]
        }
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>/timeline', methods=['GET'])
def get_timeline(id):
    try:
        transactions = db_session.query(Transaction).filter(Transaction.person_id == id).order_by(Transaction.transaction_date.asc()).all()
        dates = []
        amounts = []
        cumulative = []
        current = 0
        for t in transactions:
            dates.append(t.transaction_date.isoformat())
            amt = t.amount if t.type == 'deposit' else -t.amount
            amounts.append(amt)
            current += amt
            cumulative.append(current)
        
        return jsonify({"success": True, "data": {"dates": dates, "amounts": amounts, "cumulative": cumulative}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/merge', methods=['POST'])
def merge():
    try:
        req = request.json
        merge_persons(req.get('source_ids', []), req.get('target_id'))
        return jsonify({"success": True, "data": {}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>/split', methods=['POST'])
def split(id):
    try:
        req = request.json
        new_person_id = split_alias(id, req.get('alias_id'))
        return jsonify({"success": True, "data": {"new_person_id": new_person_id}})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>', methods=['PUT'])
def update(id):
    try:
        req = request.json
        p = db_session.query(Person).get(id)
        if p:
            if 'display_name' in req:
                p.display_name = req['display_name']
            if 'memo' in req:
                p.memo = req['memo']
            db_session.commit()
            return jsonify({"success": True, "data": {}})
        return jsonify({"success": False, "error": "Not found"})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>', methods=['DELETE'])
def delete_person(id):
    try:
        p = db_session.query(Person).get(id)
        if p:
            # Set transactions person_id to null
            db_session.query(Transaction).filter(Transaction.person_id == id).update({"person_id": None})
            db_session.query(PersonAlias).filter(PersonAlias.person_id == id).delete()
            db_session.delete(p)
            db_session.commit()
        return jsonify({"success": True, "data": {}})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
