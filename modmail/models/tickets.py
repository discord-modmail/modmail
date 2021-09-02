from sqlalchemy import Column, Integer

from modmail.models.base import Base


class Tickets(Base):
    """
    An discord modmail ticket for a Discord user with id `creater_id`.

    * <id>: internal ticket ID for modmail, not for users.
    * <server_id>: ticket creation guild.
    * <thread_id>: thread created for this ticket. Since threads won't
        have the same ID even across guilds, they would be unique so that two
        tickets aren't created.
    * <creater_id>: ticket opener's discord user ID.
    * <creating_message_id>: message ID which created this ticket, if
        it was opened with DMing the bot, it would be that of the DM channel,
        if it was opened with running a command on the guild, it would be that.
    * <creating_channel_id>: channel ID the thread was created in.
    """

    id = Column(Integer, primary_key=True, unique=True)
    server_id = Column(Integer)
    thread_id = Column(Integer, unique=True)
    creater_id = Column(Integer)
    creating_message_id = Column(Integer)
    creating_channel_id = Column(Integer)
