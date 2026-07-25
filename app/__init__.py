import os

from flask import Flask

from config import Config

from .extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_uri.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(db_uri.replace("sqlite:///", "")), exist_ok=True)

    db.init_app(app)

    from . import auth, items, search, admin

    app.register_blueprint(auth.bp)
    app.register_blueprint(items.bp)
    app.register_blueprint(search.bp)
    app.register_blueprint(admin.bp)

    with app.app_context():
        db.create_all()
        from .seed import seed_defaults

        seed_defaults()

    from .fields import get_options

    app.jinja_env.globals["field_options"] = get_options

    @app.template_filter("dt")
    def format_datetime(value, fmt="%Y-%m-%d %H:%M"):
        if not value:
            return ""
        return value.strftime(fmt)

    return app
