from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from app.config import Config
from app.models import init_db, verify_admin


def create_app():
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / "templates"),
        static_folder=str(Path(__file__).parent.parent / "static"),
    )
    app.config.from_object(Config)

    init_db()

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        if user_id == "1":
            return __import__("app.auth_user", fromlist=["AdminUser"]).AdminUser(
                1, Config.ADMIN_USERNAME
            )
        return None

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    return app
