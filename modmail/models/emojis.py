from sqlalchemy import Boolean, Column, Integer, String

from modmail.models.base import Base


class Emojis(Base):
    """Database model representing a discord emoji."""

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    animated = Column(Boolean, default=False)
