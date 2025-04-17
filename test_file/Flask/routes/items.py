from flask import request, jsonify
from models import Item, db
from utils import token_required
from routes import items_bp

@items_bp.route('', methods=['GET'])
@token_required
def get_all_items(current_user):
    """Get all items for the current user."""
    items = Item.query.filter_by(user_id=current_user.id).all()
    
    # Convert items to dictionaries
    result = [item.to_dict() for item in items]
    
    return jsonify(result)

@items_bp.route('/<item_id>', methods=['GET'])
@token_required
def get_one_item(current_user, item_id):
    """Get a specific item by ID."""
    item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
    
    if not item:
        return jsonify({'message': 'Item not found'}), 404
        
    return jsonify(item.to_dict())

@items_bp.route('', methods=['POST'])
@token_required
def create_item(current_user):
    """Create a new item."""
    data = request.get_json()
    
    # Check required fields
    if not data or not data.get('name'):
        return jsonify({'message': 'Missing required fields'}), 400
        
    # Create new item
    new_item = Item(
        name=data['name'],
        description=data.get('description', ''),
        user_id=current_user.id
    )
    
    # Add to database
    db.session.add(new_item)
    db.session.commit()
    
    return jsonify(new_item.to_dict()), 201

@items_bp.route('/<item_id>', methods=['PUT'])
@token_required
def update_item(current_user, item_id):
    """Update an existing item."""
    data = request.get_json()
    
    # Find item
    item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
    
    if not item:
        return jsonify({'message': 'Item not found'}), 404
        
    # Update fields
    if 'name' in data:
        item.name = data['name']
    if 'description' in data:
        item.description = data['description']
        
    # Save changes
    db.session.commit()
    
    return jsonify(item.to_dict())

@items_bp.route('/<item_id>', methods=['DELETE'])
@token_required
def delete_item(current_user, item_id):
    """Delete an item."""
    # Find item
    item = Item.query.filter_by(id=item_id, user_id=current_user.id).first()
    
    if not item:
        return jsonify({'message': 'Item not found'}), 404
        
    # Delete from database
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'message': 'Item deleted'}), 204