import os
from flask import Flask, jsonify
from flask_cors import CORS
from models import db
from config import config
from routes import auth_bp, items_bp

def create_app(config_name='default'):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Enable CORS
    CORS(app)
    
    # Initialize extensions
    db.init_app(app)
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(items_bp)
    
    # Create database tables (if they don't exist)
    with app.app_context():
        db.create_all()
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({'status': 'healthy'})
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': 'Not found'}), 404
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'message': 'Bad request'}), 400
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'message': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    # Get the environment from environment variable or use development by default
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Create the app with the specified environment
    app = create_app(env)
    
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)