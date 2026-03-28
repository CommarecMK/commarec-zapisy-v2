"""
app/__init__.py — Flask application factory.

Vytvoří a nakonfiguruje Flask aplikaci, zaregistruje blueprinty,
inicializuje databázi a spustí migrace.
"""
import os
import json as _json
from flask import Flask
from werkzeug.security import generate_password_hash
from .extensions import db


def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # ─── Konfigurace ──────────────────────────────────────────────────────────
    app.secret_key = os.environ.get("SECRET_KEY", "change-this-in-production")

    database_url = os.environ.get("DATABASE_URL", "sqlite:///zapisy.db")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    app.config["SQLALCHEMY_DATABASE_URI"]      = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["JSON_AS_ASCII"]                = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"]    = {"pool_pre_ping": True}

    # ─── Jinja2 filtry ────────────────────────────────────────────────────────
    app.jinja_env.filters["fromjson"]       = lambda s: _json.loads(s) if s else {}
    app.jinja_env.filters["regex_replace"]  = (
        lambda s, pattern, repl: __import__("re").sub(pattern, repl, s) if s else ""
    )

    # ─── Inicializace rozšíření ───────────────────────────────────────────────
    db.init_app(app)
    from .extensions import migrate as _migrate
    from . import models as _models  # noqa: zajistí registraci modelů v Alembic
    _migrate.init_app(app, db)

    # ─── Registrace blueprintů ────────────────────────────────────────────────
    from .routes.main    import bp as main_bp
    from .routes.klienti import bp as klienti_bp
    from .routes.nabidky import bp as nabidky_bp
    from .routes.zapisy  import bp as zapisy_bp
    from .routes.freelo  import bp as freelo_bp
    from .routes.admin   import bp as admin_bp
    from .routes.report  import bp as report_bp
    from .routes.portal  import bp as portal_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(klienti_bp)
    app.register_blueprint(nabidky_bp)
    app.register_blueprint(zapisy_bp)
    app.register_blueprint(freelo_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(report_bp)
    app.register_blueprint(portal_bp)

    # ─── Error handlery ───────────────────────────────────────────────────────
    from flask import render_template

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("500.html"), 500

    # ─── DB init + migrace ────────────────────────────────────────────────────
    with app.app_context():
        _init_db(app)

    return app


def _init_db(app):
    """Inicializuje DB, spustí migrace a seed data."""
    from .models import User, Klient, Zapis, Projekt, Nabidka, NabidkaPolozka, TemplateConfig
    from .seed import seed_test_data
    from .services.ai_service import assemble_output_text
    from .config import TEMPLATE_SECTIONS

    try:
        # db.create_all() jako záchranná síť pro nové instalace bez migrations/
        # V produkci a stagingu se schéma spravuje přes: flask db upgrade
        db.create_all()

        # Výchozí admin
        if not User.query.filter_by(email="admin@commarec.cz").first():
            try:
                db.session.add(User(
                    email="admin@commarec.cz", name="Admin", role="superadmin",
                    password_hash=generate_password_hash(
                        os.environ.get("ADMIN_PASSWORD") or __import__("secrets").token_urlsafe(16)
                    ), is_admin=True
                ))
                db.session.commit()
                pwd_display = os.environ.get("ADMIN_PASSWORD") or "(nahodne - viz log)"
                print(f"Vytvoren vychozi admin: admin@commarec.cz")
                if not os.environ.get("ADMIN_PASSWORD"):
                    print("POZOR: Nastav ADMIN_PASSWORD env var na Railway!")
            except Exception:
                db.session.rollback()

        # Seed testovacích dat — POUZE pokud ENABLE_SEED=true
        if os.environ.get("ENABLE_SEED", "").lower() == "true":
            try:
                seed_test_data()
                print("Seed: testovaci data vytvorena")
            except Exception as e:
                print(f"Seed error: {e}")
            try:
                import importlib.util
                import os as _os
                _path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "seed_extra.py")
                if _os.path.exists(_path):
                    _spec = importlib.util.spec_from_file_location("seed_extra", _path)
                    _mod = importlib.util.module_from_spec(_spec)
                    _spec.loader.exec_module(_mod)
                    _mod.seed_extra_data(
                        db, Klient, Projekt, Zapis, User,
                        TEMPLATE_SECTIONS, assemble_output_text,
                        generate_password_hash
                    )
            except Exception as e:
                print(f"Extra seed error: {e}")

    except Exception as e:
        print(f"DB init error: {e}")
