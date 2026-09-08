from logging.config import fileConfig
import sys
from pathlib import Path

# Ensure backend directory is in sys.path for app module imports
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import GeoAlchemy2 so its Alembic hooks and type comparators are registered
import geoalchemy2  # noqa: F401

from sqlalchemy import pool
from alembic import context

# Centralized settings and engine
from app.core.config import settings
from app.db.session import engine

# Import all models to ensure complete metadata registration
from app.models import (
    Base,
    Parcel,
    Building,
    Floor,
    Unit,
    Owner,
    OwnershipRight,
    ULPIN3D,
)

# Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Dynamically set sqlalchemy.url from application settings without hardcoding credentials
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    """
    Exclude PostGIS system, topology, and tiger geocoder tables/views from autogenerate.
    Only tables defined in the application's target_metadata are managed.
    """
    if type_ == "table":
        if reflected and name not in target_metadata.tables:
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode using the application engine."""
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
