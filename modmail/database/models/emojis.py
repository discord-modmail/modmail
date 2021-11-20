from tortoise import fields
from tortoise.models import Model

from .messages import Messages


class Emojis(Model):
    """Database model representing a custom discord emoji."""

    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=32)
    url = fields.TextField()
    animated = fields.BooleanField(default=False)
    message_id: fields.ForeignKeyRelation[Messages] = fields.ForeignKeyField(
        "models.Messages", related_name="emojis", to_field="id"
    )
