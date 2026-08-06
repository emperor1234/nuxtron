import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Make `app.*` importable the same way the rest of the codebase does,
# regardless of which directory `alembic` is invoked from.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import every module that defines a model, so Base.metadata is fully
# populated before autogenerate compares against it. This mirrors the actual
# live import surface (routers/crm.py, routers/lindy_email_management.py,
# etc. import these at app startup) — if a new model file is added, it must
# be imported here too or autogenerate will silently miss it.
import app.models  # noqa: E402,F401
import app.models_lindy_email  # noqa: E402,F401
import app.models_lindy_meeting  # noqa: E402,F401
import app.stores.notifications  # noqa: E402,F401
from app.database import Base, _get_database_url  # noqa: E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _resolve_url() -> str:
    """Resolve the database URL the same way app.database does at runtime.

    Falls back to a local SQLite file (not :memory:, so multiple alembic
    invocations in the same process/CLI session see the same DB) only when
    no DATABASE_URL/POSTGRES_* env vars are set — i.e. for local
    `alembic revision --autogenerate` runs without a Postgres instance handy.
    Never used silently in production: app.database.init_db() refuses to
    boot against Postgres without a real alembic_version table (see its
    docstring), so a misconfigured URL here shows up immediately as "nothing
    to migrate" rather than a silent divergence.
    """
    url = _get_database_url()
    if url:
        return url
    return 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '_alembic_local.db')


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=_resolve_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    ini_section = config.get_section(config.config_ini_section, {})
    ini_section['sqlalchemy.url'] = _resolve_url()
    connectable = engine_from_config(
        ini_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
