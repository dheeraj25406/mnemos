from datetime import datetime, timezone
from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# Naming convention for database constraints to ensure clean migrations
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


# Sentinel high timestamp for open half-open intervals [from, to)
SENTINEL_MAX_TIME = datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=convention)
