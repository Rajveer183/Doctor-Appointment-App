from sqlalchemy import event
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

IS_SQLITE = make_url(settings.database_url).get_backend_name() == "sqlite"

_engine_kwargs: dict = {"echo": False}
if not IS_SQLITE:
    # Cloud Run gives every instance its own pool, and Cloud SQL closes idle
    # connections, so keep the pool small and recycle before that happens.
    _engine_kwargs.update(pool_size=5, max_overflow=0, pool_recycle=1800, pool_pre_ping=True)

engine = create_async_engine(settings.database_url, **_engine_kwargs)


# --- SQLite-only concurrency setup -------------------------------------------------
# SQLite has no row-level locking (no `SELECT ... FOR UPDATE`) — it's a single-writer
# database. The closest real equivalent is forcing every transaction to grab the
# write lock immediately on BEGIN, instead of SQLite's default "deferred" begin that
# only locks once a write statement runs. That turns a read-then-write race between
# two booking requests into a serialized queue: the second transaction blocks at BEGIN
# until the first commits, rather than both reading "open" and both trying to write.
#
# This block is guarded by IS_SQLITE because neither piece is portable: PRAGMA is not
# Postgres syntax, and `BEGIN IMMEDIATE` is a syntax error there. On Postgres the same
# guarantee comes from SELECT ... FOR UPDATE on the slot row — see commands.md,
# "Required before real traffic".
if IS_SQLITE:

    @event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        # Wait for a contended write lock instead of failing instantly.
        cursor.execute("PRAGMA busy_timeout=5000")
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
