from sqlalchemy import Column, Integer

from modmail.models.base import Base


class Tickets(Base):
    """An discord modmail ticket for a Discord user with id `creater_id`."""

    id = Column(Integer, primary_key=True, unique=True)
    server_id = Column(Integer)
    thread_id = Column(Integer)
    creater_id = Column(Integer)
    creating_message_id = Column(Integer)
    creating_channel_id = Column(Integer)
