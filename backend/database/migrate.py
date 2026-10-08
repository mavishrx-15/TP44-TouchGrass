"""Apply numbered SQL migrations once, for PostgreSQL or local SQLite."""

import sqlite3
from pathlib import Path

from sqlalchemy.engine import make_url

from app.config import settings

MIGRATIONS = Path(__file__).parent / "migrations"


def main() -> None:
    url = make_url(settings.database_url)
    if url.drivername.startswith("sqlite"):
        connection = sqlite3.connect(url.database)
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if connection.execute("SELECT 1 FROM schema_migrations WHERE name=?", (path.name,)).fetchone():
                continue
            connection.executescript(path.read_text())
            connection.execute("INSERT INTO schema_migrations VALUES (?)", (path.name,))
            connection.commit()
        connection.close()
        return

    import psycopg2

    dsn = url.set(drivername="postgresql").render_as_string(hide_password=False)
    connection = psycopg2.connect(dsn)
    try:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
                for path in sorted(MIGRATIONS.glob("*.sql")):
                    cursor.execute("SELECT 1 FROM schema_migrations WHERE name=%s", (path.name,))
                    if cursor.fetchone():
                        continue
                    cursor.execute(path.read_text())
                    cursor.execute("INSERT INTO schema_migrations VALUES (%s)", (path.name,))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
