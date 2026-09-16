from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)


# SQLite has no row-level locking (no `SELECT ... FOR UPDATE`) — it's a single-writer
# database. The closest real equivalent is forcing every transaction to grab the
# write lock immediately on BEGIN, instead of SQLite's default "deferred" begin that
# only locks once a write statement runs. That turns a read-then-write race between
# two booking requests into a serialized queue: the second transaction blocks at BEGIN
# until the first commits, rather than both reading "open" and both trying to write.
# WAL mode is enabled so readers (GET requests) aren't blocked by that writer lock.
@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()
    dbapi_connection.isolation_level = None


@event.listens_for(engine.sync_engine, "begin")
def _begin_immediate(conn):
    conn.exec_driver_sql("BEGIN IMMEDIATE")


SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
