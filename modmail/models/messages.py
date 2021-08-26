from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from modmail.models.base import Base


class Messages(Base):
    """Database model representing a message sent in a modmail ticket."""

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("ticket.id"))
    mirrored_id = Column(Integer)
    author_id = Column(Integer)
    content = Column(String)
    internal = Column(Boolean, default=False)
