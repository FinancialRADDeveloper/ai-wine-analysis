"""
Database connection management.

Uses SQLAlchemy Core (not ORM) for query building. This is deliberate:
- Core gives SQL-level control needed for bi-temporal queries
- No magic object-relational mapping that obscures what hits the DB
- Financial systems value explicit, auditable SQL over convenience

Finance analogy:
- This is the "database adapter" that every service uses
- Connection pooling, health checks, and clean teardown
"""

import os
from functools import lru_cache

from sqlalchemy import create_engine, Engine


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """
    Create a SQLAlchemy engine from environment config.
    Cached so the entire application shares one connection pool.
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://sommelier:sommelier_dev@localhost:5432/sommelier",
    )
    return create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections are alive before use
        echo=False,  # Set True for SQL debugging
    )
