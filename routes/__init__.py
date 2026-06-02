from flask import Blueprint

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/api/dashboard')
people_bp = Blueprint('people', __name__, url_prefix='/api/people')
stocks_bp = Blueprint('stocks', __name__, url_prefix='/api/stocks')
upload_bp = Blueprint('upload', __name__, url_prefix='/api/upload')
accounts_bp = Blueprint('accounts', __name__, url_prefix='/api/accounts')

# Import route modules so their view functions are registered on the blueprints.
from routes import accounts, dashboard, people, stocks, upload  # noqa: E402,F401
