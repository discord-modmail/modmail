from sqlalchemy import Column, Integer, String

from modmail.models.base import Base


class Configurations(Base):
    """Database model representing a discord modmail bot configurations.."""

    server_id = Column(Integer)
    thread_id = Column(Integer, nullable=True)
    config_key = Column(String)
    config_value = Column(String)
