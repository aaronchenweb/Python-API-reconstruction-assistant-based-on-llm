from flask import request, jsonify
from models import User, db
from utils import generate_token
from routes import auth_bp

@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.get_json()
    
    # Check required fields
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing required fields'}), 400
        
    # Check if user already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'User already exists'}), 409
        
    # Create new user
    new_user = User(
        username=data['username'],
        password=data['password'],
        admin=data.get('admin', False)
    )
    
    # Add to database
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate a user and return a token."""
    data = request.get_json()
    
    # Check required fields
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing credentials'}), 400
        
    # Find user
    user = User.query.filter_by(username=data['username']).first()
    
    # Check password
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401
        
    # Generate token
    token = generate_token(user.id)
    
    return jsonify({
        'token': token,
        'message': 'Login successful'
    })