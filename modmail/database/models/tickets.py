from tortoise import fields
from tortoise.models import Model

from .guilds import Guilds
from .messages import Messages


class Tickets(Model):
    """An discord modmail ticket for a Discord user with id `author_id`."""

    id = fields.BigIntField(pk=True, unique=True)
    server_id: fields.ForeignKeyRelation[Guilds] = fields.ForeignKeyField(
        "models.Guilds",
        related_name="tickets",
        to_field="id",
    )
    thread_id = fields.BigIntField(unique=True)
    author_id = fields.BigIntField()
    creating_message_id: fields.ForeignKeyRelation[Messages] = fields.ForeignKeyField(
        "models.Messages",
        related_name="ticket_creations",
        to_field="id",
    )
    creating_channel_id = fields.BigIntField()
