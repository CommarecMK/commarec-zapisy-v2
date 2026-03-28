"""
extensions.py — sdílené instance (db, migrate) a env proměnné.
Importuje se všude — nevytváří Flask app.
"""
import os
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

# ─── Env proměnné ─────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
FREELO_API_KEY    = os.environ.get("FREELO_API_KEY", "")
FREELO_EMAIL      = os.environ.get("FREELO_EMAIL", "")
FREELO_PROJECT_ID = os.environ.get("FREELO_PROJECT_ID", "501350")
