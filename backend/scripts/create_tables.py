"""Create any missing tables. Non-destructive.

This exists because the only schema creation in the repo lives in app/seed.py, which
calls drop_all() first — safe for a local demo reset, catastrophic against a real
database. app/main.py never creates tables at all, so a fresh deployment 500s on
every endpoint until something runs this.

    Local:     python -m scripts.create_tables
    Cloud Run: deployed as a Job, see step 6 of commands.md

This is create_all, not migrations: it adds tables that don't exist yet and ignores
ones that do. It will NOT alter an existing table when you change a column. Once the
schema starts changing under real data, replace this with Alembic.
"""
import asyncio

from app.database import Base, engine
import app.models  # noqa: F401  — importing registers every table on Base.metadata


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Schema is up to date.")


if __name__ == "__main__":
    asyncio.run(main())
