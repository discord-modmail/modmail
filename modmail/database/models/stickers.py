from tortoise import fields
from tortoise.models import Model

from .messages import Messages


class Stickers(Model):
    """Database model representing a custom discord sticker."""

    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=32)
    url = fields.TextField()
    message_id: fields.ForeignKeyRelation[Messages] = fields.ForeignKeyField(
        "models.Messages", related_name="stickers", to_field="id"
    )
