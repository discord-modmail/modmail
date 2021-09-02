from sqlalchemy import Column, Integer, String

from modmail.models.base import Base


class Configurations(Base):
    """
    Database model representing a discord modmail bot configurations.

    * <target_id>: target ID according to the level of the configuration. It can
        either be the bot ID or the server ID or a thread ID. If it is a
            bot ID: global level, across all its servers.
            server ID: server level, acorss all its threads.
            thread ID: thread level, for that specific server thread.
    * <config_key>: The configuration name
    * <config_value>: The configuration value
    """

    target_id = Column(Integer, primary_key=True, nullable=False)
    config_key = Column(String)
    config_value = Column(String)
