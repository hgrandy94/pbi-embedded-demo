import os

from flask import Flask
from flask_login import LoginManager

login_manager = LoginManager()


def create_app(config: dict | None = None):
    """Flask application factory.

    Args:
        config: Dictionary of configuration values passed from the CLI.
    """

    app = Flask(__name__)

    # Apply configuration passed in from click CLI options
    if config:
        app.config.update(config)

    # Ensure a secret key is set for session management
    app.secret_key = app.config.get("SECRET_KEY", os.urandom(24))

    # Initialise Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # Register blueprints
    from app.auth import auth_bp
    from app.views import views_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)

    return app
