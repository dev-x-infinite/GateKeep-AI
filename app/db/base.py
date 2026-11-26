from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Inheriting from DeclarativeBase provides modern SQLAlchemy 2.0
    type-annotated declarative mapping.
    """
    pass
