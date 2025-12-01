from logging.config import fileConfig

from alembic import context
from app.config import settings
from app.db.config import Base

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *  # noqa: F403
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override the database URL from settings
config.set_main_option(
    "sqlalchemy.url",
    f"postgresql://{settings.POSTGRES_DB_USER}:{settings.POSTGRES_DB_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB_NAME}",
)

# Define naming conventions for automatic constraint/index naming
naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "chk_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# Apply naming conventions to metadata
target_metadata.naming_convention = naming_convention


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Naming conventions for automatic constraint/index naming
        naming_convention=naming_convention,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # type: ignore
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Naming conventions for automatic constraint/index naming
            naming_convention=naming_convention,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
