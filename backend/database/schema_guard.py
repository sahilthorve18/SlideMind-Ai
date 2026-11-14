"""Add columns that models gained after a table was first created.

``db.create_all()`` creates missing tables and leaves existing tables unchanged.
This only adds nullable columns, so rows already in the database stay valid.
"""
import logging

from sqlalchemy import inspect, text

from database import db

log = logging.getLogger(__name__)


def add_missing_columns() -> None:
    engine = db.engine
    insp = inspect(engine)
    with engine.begin() as conn:
        for table in db.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {col["name"] for col in insp.get_columns(table.name)}
            for col in table.columns:
                if col.name in existing or col.primary_key:
                    continue
                if not col.nullable and col.server_default is None and col.default is None:
                    log.warning(
                        "Skipping new required column %s.%s; add it with a default in a migration",
                        table.name,
                        col.name,
                    )
                    continue
                ddl_type = col.type.compile(dialect=engine.dialect)
                stmt = text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {ddl_type}")
                try:
                    conn.execute(stmt)
                    log.info("Added column %s.%s", table.name, col.name)
                except Exception:
                    log.exception("Could not add column %s.%s", table.name, col.name)
