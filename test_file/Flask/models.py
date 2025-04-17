from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

db = SQLAlchemy()

class User(db.Model):
    """User model for storing user related details."""
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    registered_on = db.Column(db.DateTime, default=datetime.utcnow)
    admin = db.Column(db.Boolean, nullable=False, default=False)
    items = db.relationship('Item', backref='owner', lazy='dynamic')

    def __init__(self, username, password, admin=False):
        self.username = username
        self.password_hash = generate_password_hash(password)
        self.admin = admin

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User '{self.username}'>"

class Item(db.Model):
    """Item model for storing item related details."""
    __tablename__ = 'items'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)

    def __init__(self, name, description='', user_id=None):
        self.name = name
        self.description = description
        if user_id:
            self.user_id = user_id

    def __repr__(self):
        return f"<Item '{self.name}'>"
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'user_id': self.user_id
        }