"""initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-28

Vytvoří všechny tabulky pro Commarec Zápisy v2.
Na existující produkční DB: spusť jednou `flask db stamp head` (viz CLAUDE.md).
Na nové/staging DB: `flask db upgrade` vytvoří vše automaticky.
"""
from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ── klient ────────────────────────────────────────────────────────────────
    op.create_table(
        "klient",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nazev", sa.String(200), nullable=False),
        sa.Column("slug", sa.String(200), unique=True, nullable=False),
        sa.Column("kontakt", sa.String(200), server_default=""),
        sa.Column("email", sa.String(200), server_default=""),
        sa.Column("telefon", sa.String(60), server_default=""),
        sa.Column("adresa", sa.String(300), server_default=""),
        sa.Column("poznamka", sa.Text(), server_default=""),
        sa.Column("logo_url", sa.String(500), server_default=""),
        sa.Column("ic", sa.String(20), server_default=""),
        sa.Column("dic", sa.String(20), server_default=""),
        sa.Column("sidlo", sa.String(300), server_default=""),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("profil_json", sa.Text(), server_default="{}"),
        sa.Column("freelo_tasklist_id", sa.Integer(), nullable=True),
    )

    # ── template_config ───────────────────────────────────────────────────────
    op.create_table(
        "template_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_key", sa.String(40), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("system_prompt", sa.Text(), server_default=""),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # ── user ──────────────────────────────────────────────────────────────────
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(120), unique=True, nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("role", sa.String(40), server_default="konzultant"),
        sa.Column("klient_id", sa.Integer(), sa.ForeignKey("klient.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("freelo_email", sa.String(120), nullable=True),
        sa.Column("freelo_api_key", sa.String(200), nullable=True),
    )

    # ── projekt ───────────────────────────────────────────────────────────────
    op.create_table(
        "projekt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nazev", sa.String(200), nullable=False),
        sa.Column("popis", sa.Text(), server_default=""),
        sa.Column("klient_id", sa.Integer(), sa.ForeignKey("klient.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("datum_od", sa.Date(), nullable=True),
        sa.Column("datum_do", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("freelo_project_id", sa.Integer(), nullable=True),
        sa.Column("freelo_tasklist_id", sa.Integer(), nullable=True),
    )

    # ── zapis ─────────────────────────────────────────────────────────────────
    op.create_table(
        "zapis",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("template", sa.String(50), nullable=False),
        sa.Column("input_text", sa.Text(), nullable=False),
        sa.Column("output_json", sa.Text(), server_default="{}"),
        sa.Column("output_text", sa.Text(), server_default=""),
        sa.Column("tasks_json", sa.Text(), server_default="[]"),
        sa.Column("notes_json", sa.Text(), server_default="[]"),
        sa.Column("interni_prompt", sa.Text(), server_default=""),
        sa.Column("freelo_sent", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("public_token", sa.String(40), unique=True, nullable=True),
        sa.Column("is_public", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("klient_id", sa.Integer(), sa.ForeignKey("klient.id"), nullable=True),
        sa.Column("projekt_id", sa.Integer(), sa.ForeignKey("projekt.id"), nullable=True),
    )

    # ── nabidka ───────────────────────────────────────────────────────────────
    op.create_table(
        "nabidka",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cislo", sa.String(50), unique=True, nullable=False),
        sa.Column("klient_id", sa.Integer(), sa.ForeignKey("klient.id"), nullable=False),
        sa.Column("projekt_id", sa.Integer(), sa.ForeignKey("projekt.id"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("nazev", sa.String(300), nullable=False),
        sa.Column("poznamka", sa.Text(), server_default=""),
        sa.Column("platnost_do", sa.Date(), nullable=True),
        sa.Column("stav", sa.String(30), server_default="draft"),
        sa.Column("mena", sa.String(10), server_default="CZK"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    # ── nabidka_polozka ───────────────────────────────────────────────────────
    op.create_table(
        "nabidka_polozka",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nabidka_id", sa.Integer(), sa.ForeignKey("nabidka.id"), nullable=False),
        sa.Column("poradi", sa.Integer(), server_default="0"),
        sa.Column("nazev", sa.String(300), nullable=False),
        sa.Column("popis", sa.Text(), server_default=""),
        sa.Column("mnozstvi", sa.Numeric(10, 2), server_default="1"),
        sa.Column("jednotka", sa.String(30), server_default="ks"),
        sa.Column("cena_ks", sa.Numeric(12, 2), server_default="0"),
        sa.Column("sleva_pct", sa.Numeric(5, 2), server_default="0"),
        sa.Column("dph_pct", sa.Numeric(5, 2), server_default="0"),
    )


def downgrade():
    op.drop_table("nabidka_polozka")
    op.drop_table("nabidka")
    op.drop_table("zapis")
    op.drop_table("projekt")
    op.drop_table("user")
    op.drop_table("template_config")
    op.drop_table("klient")
