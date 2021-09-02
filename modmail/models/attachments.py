from sqlalchemy import Column, ForeignKey, Integer, String

from modmail.models.base import Base


class Attachments(Base):
    """
    Database model representing a message attachment sent in a modmail ticket.

    * <internal_id>: Internal ID for the attachment
    * <message_id>: Message ID containing this attachment
    * <link>: Discord attachment URL
    """

    internal_id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    link = Column(String)
