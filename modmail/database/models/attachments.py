from tortoise import fields
from tortoise.models import Model

from .messages import Messages


class Attachments(Model):
    """Database model representing a message attachment sent in a modmail ticket."""

    id = fields.BigIntField(pk=True)
    message_id: fields.ForeignKeyRelation[Messages] = fields.ForeignKeyField(
        "models.Messages", related_name="attachments", to_field="id"
    )
    filename = fields.CharField(max_length=255)
    file_url = fields.TextField()
