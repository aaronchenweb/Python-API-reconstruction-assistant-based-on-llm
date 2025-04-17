from flask import Blueprint

# Create blueprints
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
items_bp = Blueprint('items', __name__, url_prefix='/items')

# Import routes
from routes.auth import *
from routes.items import *