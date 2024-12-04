"""Route registration for the application."""

from flask import Flask
from .transcription import transcription_bp

def register_routes(app: Flask) -> None:
    """Register all blueprints/routes with the application.
    
    Args:
        app: The Flask application instance.
    """
    app.register_blueprint(transcription_bp) 