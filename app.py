"""Main application entry point."""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from src.config.logging import configure_logging
from src.routes import register_routes

# Load environment variables
load_dotenv()

def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=os.path.abspath('templates'),
        static_folder=os.path.abspath('static')
    )
    CORS(app)
    
    # Configure logging
    configure_logging(app)
    
    # Register routes
    register_routes(app)
    
    return app

# Create the application instance
app = create_app()

if __name__ == '__main__':
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5001,
        ssl_context=('cert.pem', 'key.pem')
    )
