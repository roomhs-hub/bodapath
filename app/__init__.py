import os

from flask import Flask

from config import Config

from .extensions import db


def _migrate_add_missing_columns():
    """db.create_all()은 기존 테이블에 새 컬럼을 추가해 주지 않으므로,
    이미 만들어진 테이블에 없는 컬럼이 있으면 여기서 직접 ALTER TABLE로 추가한다.
    SQLite(로컬 미리보기)와 PostgreSQL(운영) 모두에서 동작하는 문법만 사용한다.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "handover_item" not in inspector.get_table_names():
        return  # create_all()이 아직 테이블 자체를 안 만든 첫 실행 등

    columns = {c["name"] for c in inspector.get_columns("handover_item")}
    if "is_deleted" not in columns:
        with db.engine.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE handover_item ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )

    if "field_config" in inspector.get_table_names():
        field_config_columns = {c["name"] for c in inspector.get_columns("field_config")}
        if "is_deleted" not in field_config_columns:
            with db.engine.begin() as conn:
                conn.execute(
                    text(
                        "ALTER TABLE field_config ADD COLUMN is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )


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
        _migrate_add_missing_columns()
        from .seed import seed_defaults

        seed_defaults()

    from .fields import get_options
    from .items import MAX_LENGTHS

    app.jinja_env.globals["field_options"] = get_options
    app.jinja_env.globals["max_lengths"] = MAX_LENGTHS

    @app.template_filter("dt")
    def format_datetime(value, fmt="%Y-%m-%d %H:%M"):
        if not value:
            return ""
        return value.strftime(fmt)

    return app
