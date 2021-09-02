from sqlalchemy import JSON, Column, ForeignKey, Integer

from modmail.models.base import Base


class Embeds(Base):
    """
    Database model representing a discord embed.

    * <internal_id>: Internal ID for the embed
    * <message_id>: Message ID containing this embed
    * <json_content>: Embed represented as JSON data
    """

    internal_id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    json_content = Column(JSON)
