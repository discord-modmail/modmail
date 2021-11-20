from tortoise import fields
from tortoise.models import Model

from .messages import Messages


class Embeds(Model):
    """Database model representing a discord embed."""

    id = fields.BigIntField(pk=True)
    message_id: fields.ForeignKeyRelation[Messages] = fields.ForeignKeyField(
        "models.Messages", related_name="embeds", to_field="id"
    )
    content = fields.JSONField()
