"""Main application entry point."""

import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from src.config.logging import configure_logging
from src.routes.transcription import transcription_bp
from src.routes.long_recording import long_recording_bp

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
    
    # Register blueprints
    app.register_blueprint(transcription_bp, name='transcription_main')
    app.register_blueprint(long_recording_bp, name='long_recording_main')
    
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
