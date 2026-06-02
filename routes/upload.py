from flask import jsonify, request, current_app
import os
from werkzeug.utils import secure_filename
from routes import upload_bp
from database import db_session
from models.upload import UploadSession
from services.parser import parse_excel, detect_columns, import_transactions, import_stock_trades
from datetime import datetime

ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@upload_bp.route('/', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"})
    file = request.files['file']
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"})
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)
        
        # Create session
        session = UploadSession(
            filename=filename,
            file_type=filename.rsplit('.', 1)[1].lower()
        )
        db_session.add(session)
        db_session.commit()
        
        return jsonify({"success": True, "data": {"session_id": session.id, "filename": filename}})
    
    return jsonify({"success": False, "error": "File type not allowed"})

@upload_bp.route('/preview', methods=['POST'])
def preview():
    req = request.json
    session_id = req.get('session_id')
    try:
        session = db_session.query(UploadSession).get(session_id)
        if not session:
            return jsonify({"success": False, "error": "Session not found"})
        
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), session.filename)
        df = parse_excel(filepath)
        preview_data = df.head(10).to_dict(orient='records')
        detected = detect_columns(df)
        
        return jsonify({"success": True, "data": {
            "columns": list(df.columns),
            "preview": preview_data,
            "detected": detected
        }})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@upload_bp.route('/import', methods=['POST'])
def import_data():
    req = request.json
    session_id = req.get('session_id')
    account_id = req.get('account_id')
    data_type = req.get('data_type')
    mapping = req.get('column_mapping')
    
    try:
        session = db_session.query(UploadSession).get(session_id)
        if not session:
            return jsonify({"success": False, "error": "Session not found"})
            
        filepath = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'uploads'), session.filename)
        df = parse_excel(filepath)
        
        if data_type == 'transaction':
            res = import_transactions(df, mapping, account_id, session_id)
        else:
            res = import_stock_trades(df, mapping, account_id, session_id)
            
        session.imported_rows = res['imported']
        session.total_rows = len(df)
        session.account_id = account_id
        import json
        session.column_mapping = json.dumps(mapping)
        db_session.commit()
        
        return jsonify({"success": True, "data": res})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@upload_bp.route('/sessions', methods=['GET'])
def get_sessions():
    try:
        sessions = db_session.query(UploadSession).order_by(UploadSession.uploaded_at.desc()).all()
        data = [{
            "id": s.id,
            "filename": s.filename,
            "date": s.uploaded_at.isoformat(),
            "imported": s.imported_rows,
            "total": s.total_rows
        } for s in sessions]
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
