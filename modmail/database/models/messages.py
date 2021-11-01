from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model


if TYPE_CHECKING:
    from .attachments import Attachments
    from .embeds import Embeds
    from .emojis import Emojis
    from .stickers import Stickers


class Messages(Model):
    """Database model representing a message sent in a modmail ticket."""

    id = fields.BigIntField(pk=True)
    ticket_id = fields.BigIntField()
    mirrored_id = fields.BigIntField()
    author_id = fields.BigIntField()
    content = fields.CharField(max_length=4000)

    attachments: fields.ReverseRelation["Attachments"]
    embeds: fields.ReverseRelation["Embeds"]
    emojis: fields.ReverseRelation["Emojis"]
    stickers: fields.ReverseRelation["Stickers"]
