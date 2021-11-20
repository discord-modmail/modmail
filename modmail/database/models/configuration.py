from tortoise import fields
from tortoise.exceptions import ValidationError
from tortoise.models import Model

from .guilds import Guilds


class Configurations(Model):
    """Database model representing a discord modmail bot configurations."""

    def __init__(self, **kwargs) -> None:
        if kwargs.get("target_bot_id") and not kwargs.get("target_server_id"):
            raise ValidationError("`target_bot_id` is mutually exclusive with `target_server_id`.")
        super().__init__(**kwargs)

    target_bot_id = fields.BigIntField(null=True)
    target_server_id: fields.ForeignKeyRelation[Guilds] = fields.ForeignKeyField(
        "models.Guilds", related_name="configurations", to_field="id", null=True
    )
    config_key = fields.TextField()
    config_value = fields.TextField()
