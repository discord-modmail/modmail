from typing import Any, Dict, Mapping

from sqlalchemy import JSON, Column, ForeignKey, Integer
from sqlalchemy.orm import validates

from modmail.models.base import Base


def validate_embed_fields(fields: dict) -> None:
    """Raises a ValueError if any of the given embed fields is invalid."""
    field_validators = {
        "name": (lambda name: len(name) < 256, "Field `name` must be less than 256 characters long"),
        "value": (
            lambda field_value: len(field_value) < 1024,
            "`Field value` must be less than 1024 characters long",
        ),
        "inline": (lambda inline: isinstance(inline, bool), "Field `inline` must be of type bool."),
    }

    required_fields = ("name", "value")

    assert len(fields) < 25, "Discord limits up to 25 field objects"

    for field in fields:
        if not isinstance(field, Mapping):
            raise ValueError("Embed fields must be a mapping.")

        if not all(required_field in field for required_field in required_fields):
            raise ValueError(f"Embed fields must contain the following fields: {', '.join(required_fields)}.")

        for field_name, value in field.items():
            if field_name not in field_validators:
                raise ValueError(f"Unknown embed field field: {field_name!r}.")

            validation, assertion_msg = field_validators[field_name]
            assert validation(value), assertion_msg


def validate_embed_footer(footer: Dict[str, str]) -> None:
    """Raises a ValueError if the given footer is invalid."""
    field_validators = {
        "text": (
            lambda text: 1 < len(text) < 2048,
            "Footer `text` must not be empty or be more than 2048 characters.",
        ),
        "icon_url": (lambda: True, ""),
        "proxy_icon_url": (lambda: True, ""),
    }

    if not isinstance(footer, Mapping):
        raise ValueError("Embed footer must be a mapping.")

    for field_name, value in footer.items():
        if field_name not in field_validators:
            raise ValueError(f"Unknown embed footer field: {field_name!r}.")

        validation, assertion_msg = field_validators[field_name]
        assert validation(value), assertion_msg


def validate_embed_author(author: Any) -> None:
    """Raises a ValueError if the given author is invalid."""
    field_validators = {
        "name": (
            lambda name: 1 < len(name) < 256,
            "Embed `author` name must not be empty or be more than 256 characters.",
        ),
        "url": (lambda: True, ""),
        "icon_url": (lambda: True, ""),
        "proxy_icon_url": (lambda: True, ""),
    }

    if not isinstance(author, Mapping):
        raise ValueError("Embed author must be a mapping.")

    for field_name, value in author.items():
        if field_name not in field_validators:
            raise ValueError(f"Unknown embed author field: {field_name!r}.")

        validation, assertion_msg = field_validators[field_name]
        assert validation(value), assertion_msg


def validate_embed_title(title: str) -> None:
    """Raises a ValueError if the given title is invalid."""
    assert 1 < len(title) < 256, "Embed `title` must not be empty or be more than 256 characters."


def validate_embed_description(description: str) -> None:
    """Raises a ValueError if the given title is invalid."""
    assert len(description) < 2048, "Embed `description` must not be more than 2048 characters."


class Embeds(Base):
    """Database model representing a discord embed."""

    internal_id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("messages.id"))
    json_content = Column(JSON)

    @validates("json_content")
    def validate_json_content(self, _: str, embed: Any) -> None:
        """
        Validate a JSON document containing an embed as possible to send on Discord.

        This attempts to rebuild the validation used by Discord
        as well as possible by checking for various embed limits so we can
        ensure that any embed we store here will also be accepted as a
        valid embed by the Discord API.

        Raises ValueError, if the given embed is deemed invalid.
        """
        all_keys = {
            "title",
            "type",
            "description",
            "url",
            "timestamp",
            "color",
            "footer",
            "image",
            "thumbnail",
            "video",
            "provider",
            "author",
            "fields",
        }
        one_required_of = {"description", "fields", "image", "title", "video"}
        field_validators = {
            "title": validate_embed_title,
            "description": validate_embed_description,
            "fields": validate_embed_fields,
            "footer": validate_embed_footer,
            "author": validate_embed_author,
        }

        if not embed:
            raise ValueError("Embed must not be empty.")

        elif not isinstance(embed, Mapping):
            raise ValueError("Embed must be a mapping.")

        elif not any(field in embed for field in one_required_of):
            raise ValueError(f"Embed must contain one of the fields {one_required_of}.")

        for required_key in one_required_of:
            if required_key in embed and not embed[required_key]:
                raise ValueError(f"Key {required_key!r} must not be empty.")

        for field_name, value in embed.items():
            if field_name not in all_keys:
                raise ValueError(f"Unknown field name: {field_name!r}")

            if field_name in field_validators:
                field_validators[field_name](value)
