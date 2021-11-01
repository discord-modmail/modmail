from tortoise import fields
from tortoise.models import Model

from .servers import Servers


class Tickets(Model):
    """An discord modmail ticket for a Discord user with id `creator_id`."""

    id = fields.BigIntField(pk=True, unique=True)
    server_id: fields.ForeignKeyRelation[Servers] = fields.ForeignKeyField(
        "models.Servers",
        related_name="tickets",
        to_field="id",
    )
    thread_id = fields.BigIntField(unique=True)
    creater_id = fields.BigIntField()
    creating_message_id = fields.BigIntField()
    creating_channel_id = fields.BigIntField()
