import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app
from models import User

def token_required(f):
    """Decorator function for JWT token authentication"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            # Decode the token
            data = jwt.decode(
                token, 
                current_app.config['SECRET_KEY'],
                algorithms=['HS256']
            )
            current_user = User.query.filter_by(id=data['sub']).first()
            
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
                
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
            
        return f(current_user, *args, **kwargs)
    
    return decorated

def generate_token(user_id):
    """Generate a JWT token for authentication"""
    try:
        # Token expiration time
        expiration = datetime.datetime.utcnow() + current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', datetime.timedelta(hours=1))
        
        # Token payload
        payload = {
            'exp': expiration,
            'iat': datetime.datetime.utcnow(),
            'sub': user_id
        }
        
        # Generate token
        token = jwt.encode(
            payload,
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )
        
        return token
        
    except Exception as e:
        return str(e)