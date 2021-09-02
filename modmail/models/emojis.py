from sqlalchemy import Boolean, Column, Integer, String

from modmail.models.base import Base


class Emojis(Base):
    """
    Database model representing a custom discord emoji.

    * <id>: emoji ID for server emojis
    * <name>: emoji name
    * <url>: discord emoji URL
    * <animated>: whether the emojis is animated or not
    """

    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    animated = Column(Boolean, default=False)
