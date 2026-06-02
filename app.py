from flask import Flask, render_template
from flask_cors import CORS
from database import init_db, db_session
from routes import dashboard_bp, people_bp, stocks_bp, upload_bp, accounts_bp

app = Flask(__name__)
app.config.from_pyfile('config.py')
CORS(app)

# 데이터베이스 초기화
init_db()

# 라우트 등록
app.register_blueprint(dashboard_bp)
app.register_blueprint(people_bp)
app.register_blueprint(stocks_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(accounts_bp)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()

# 페이지 라우트
@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/people')
def people():
    return render_template('people.html')

@app.route('/people/<int:id>')
def people_detail(id):
    return render_template('people_detail.html')

@app.route('/stocks')
def stocks():
    return render_template('stocks.html')

@app.route('/stocks/<int:id>')
def stock_detail(id):
    return render_template('stock_detail.html')

@app.route('/upload')
def upload():
    return render_template('upload.html')

@app.route('/accounts')
def accounts():
    return render_template('accounts.html')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
