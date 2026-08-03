from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import our Base and the models so Alembic can read them
from app.core.config import DATABASE_URL
from app.core.database import Base
from app.modules.orders.models import OrderItemModel, OrderModel  # noqa
from app.modules.products.models import ProductModel  # noqa
from app.modules.scheduling.models import AvailableDateModel  # noqa

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return DATABASE_URL


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
