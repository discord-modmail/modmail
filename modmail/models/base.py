from operator import itemgetter
from typing import Any

from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    Base model class.

    Provides functionality
     - automatically create table name
     - adds `__repr__()` to display model class name and initialisation parameters
    """

    id: Any
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:  # noqa: N805
        """Generate __tablename__ automatically for a DB model."""
        return cls.__name__.lower()

    def __repr__(self) -> str:
        """Returns the current model class name and initialisation parameters."""
        attributes = " ".join(
            f"{attribute}={value!r}"
            for attribute, value in sorted(self.__dict__.items(), key=itemgetter(0))
            if not attribute.startswith("_")
        )
        return f"<{self.__class__.__name__}({attributes})>"
