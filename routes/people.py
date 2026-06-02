from flask import jsonify, request
from routes import people_bp
from database import db_session
from models.person import Person, PersonAlias
from models.transaction import Transaction
from services.person_matcher import merge_persons, split_alias
from sqlalchemy import func

@people_bp.route('', methods=['GET'])
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

@people_bp.route('/aliases', methods=['GET'])
def get_aliases():
    try:
        aliases = db_session.query(PersonAlias).join(Person).all()
        data = []
        for alias in aliases:
            deposits = (
                db_session.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.person_alias_id == alias.id,
                    Transaction.type == 'deposit',
                )
                .scalar()
                or 0
            )
            withdrawals = (
                db_session.query(func.sum(Transaction.amount))
                .filter(
                    Transaction.person_alias_id == alias.id,
                    Transaction.type == 'withdrawal',
                )
                .scalar()
                or 0
            )
            tx_count = (
                db_session.query(func.count(Transaction.id))
                .filter(Transaction.person_alias_id == alias.id)
                .scalar()
                or 0
            )
            last_seen = (
                db_session.query(func.max(Transaction.transaction_date))
                .filter(Transaction.person_alias_id == alias.id)
                .scalar()
            )
            data.append({
                "alias_id": alias.id,
                "alias_name": alias.alias_name,
                "person_id": alias.person_id,
                "person_name": alias.person.display_name if alias.person else None,
                "total_deposit": int(deposits),
                "total_withdrawal": int(withdrawals),
                "activity_amount": int(deposits) + int(withdrawals),
                "tx_count": int(tx_count),
                "last_seen": last_seen.isoformat() if last_seen else None,
            })
        data.sort(key=lambda row: row["activity_amount"], reverse=True)
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

@people_bp.route('/merge-aliases', methods=['POST'])
def merge_aliases():
    try:
        req = request.get_json(silent=True) or {}
        alias_ids = [int(aid) for aid in req.get('alias_ids', [])]
        target_person_id = req.get('target_person_id')
        target_name = (req.get('target_name') or '').strip()

        if len(alias_ids) < 2:
            return jsonify({"success": False, "error": "합칠 예금자명을 2개 이상 선택하세요."})

        aliases = (
            db_session.query(PersonAlias)
            .filter(PersonAlias.id.in_(alias_ids))
            .all()
        )
        if len(aliases) != len(set(alias_ids)):
            return jsonify({"success": False, "error": "선택한 예금자명 중 일부를 찾을 수 없습니다."})

        if target_person_id:
            target = db_session.query(Person).get(int(target_person_id))
            if not target:
                return jsonify({"success": False, "error": "대상 인물을 찾을 수 없습니다."})
        else:
            target = aliases[0].person

        if target_name:
            target.display_name = target_name

        source_person_ids = {alias.person_id for alias in aliases if alias.person_id != target.id}
        moved_aliases = 0
        moved_transactions = 0

        for alias in aliases:
            if alias.person_id != target.id:
                alias.person_id = target.id
                moved_aliases += 1
            moved_transactions += (
                db_session.query(Transaction)
                .filter(Transaction.person_alias_id == alias.id)
                .update({"person_id": target.id}, synchronize_session=False)
            )

        for person_id in source_person_ids:
            person = db_session.query(Person).get(person_id)
            if not person:
                continue
            alias_count = (
                db_session.query(func.count(PersonAlias.id))
                .filter(PersonAlias.person_id == person_id)
                .scalar()
                or 0
            )
            tx_count = (
                db_session.query(func.count(Transaction.id))
                .filter(Transaction.person_id == person_id)
                .scalar()
                or 0
            )
            if alias_count == 0 and tx_count == 0:
                db_session.delete(person)

        db_session.commit()
        return jsonify({
            "success": True,
            "data": {
                "target_person_id": target.id,
                "moved_aliases": moved_aliases,
                "moved_transactions": moved_transactions,
            },
        })
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})

@people_bp.route('/<int:id>/split', methods=['POST'])
def split(id):
    try:
        req = request.get_json(silent=True) or {}
        data = split_alias(id, req.get('alias_id'))
        return jsonify({"success": True, "data": data})
    except Exception as e:
        db_session.rollback()
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
            db_session.query(Transaction).filter(Transaction.person_alias_id.in_(
                db_session.query(PersonAlias.id).filter(PersonAlias.person_id == id)
            )).update({"person_alias_id": None}, synchronize_session=False)
            db_session.query(PersonAlias).filter(PersonAlias.person_id == id).delete()
            db_session.delete(p)
            db_session.commit()
        return jsonify({"success": True, "data": {}})
    except Exception as e:
        db_session.rollback()
        return jsonify({"success": False, "error": str(e)})
