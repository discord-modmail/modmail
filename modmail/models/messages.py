from sqlalchemy import Column, Integer, String

from modmail.models.base import Base


class Messages(Base):
    """
    Database model representing a message sent in a modmail ticket.

    * <id>: message ID, message IDs are unique
    * <ticket_id>: modmail ticket ID, the thread created in the guild,
        in which this message was sent.
    * <mirrored_id>: mirrored message ID, sent in the guild thread.
    * <author_id>: author ID, would either be the moderator
        who sent message in the channel, or the user who has this ticket
        opened.
    * <content>: message content.
    """

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer)
    mirrored_id = Column(Integer)
    author_id = Column(Integer)
    content = Column(String)
