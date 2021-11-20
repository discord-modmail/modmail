from typing import TYPE_CHECKING

from tortoise import fields
from tortoise.models import Model


if TYPE_CHECKING:
    from .configuration import Configurations
    from .tickets import Tickets


class Guilds(Model):
    """Database model representing a discord guild."""

    id = fields.BigIntField(pk=True, null=False)
    name = fields.CharField(max_length=200)
    icon_url = fields.TextField()

    configurations: fields.ReverseRelation["Configurations"]
    tickets: fields.ReverseRelation["Tickets"]
