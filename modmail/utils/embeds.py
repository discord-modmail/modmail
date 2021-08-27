from typing import List, Tuple, Union

import discord
from discord.embeds import EmptyEmbed

original_init = discord.Embed.__init__


def __init__(self: discord.Embed, **kwargs):  # noqa: N807
    """
    Overrides discord.Embed.__init__ to add new arguments.

    Parameters
    * thumbnail
    * footer_text
    * footer_icon
    * image
    * author (a discord.User), author_name, author_icon, author_url
    * fields (a list of ("name", "value") or ("name", "value", inline))

    Also, the original arguments are still supported:
    * title
    * type
    * color
    * colour
    * url
    * description
    * timestamp
    """
    original_init(
        self,
        title=kwargs.pop("title", EmptyEmbed),
        description=kwargs.pop("description", kwargs.pop("content", EmptyEmbed)),
        type=kwargs.pop("type", "rich"),
        url=kwargs.pop("url", EmptyEmbed),
        colour=kwargs.pop("color", None) or kwargs.pop("colour", 0xE67E22),
        timestamp=kwargs.pop("timestamp", EmptyEmbed),
    )

    self.set_thumbnail(url=kwargs.pop("thumbnail", EmptyEmbed))
    self.set_footer(
        text=kwargs.pop("footer_text", EmptyEmbed),
        icon_url=kwargs.pop("footer_icon", EmptyEmbed),
    )
    self.set_image(url=kwargs.pop("image_url", kwargs.pop("image", EmptyEmbed)))

    author_name = kwargs.pop("author_name", None)
    author_icon = kwargs.pop("author_icon", None)
    author_url = kwargs.pop("author_url", EmptyEmbed)
    author: discord.User = kwargs.pop("author", None)
    if author is not None or author_name is not None:
        self.set_author(
            name=author_name if author_name is not None else author.name,
            url=author_url,
            icon_url=author_icon or str(author.display_avatar.url),
        )

    fields: List[Union[Tuple[str, str], Tuple[str, str, bool]]] = kwargs.pop("fields", [])
    for field in fields:
        if isinstance(field, dict):
            self.add_field(**field)
        elif len(field) == 3:
            name, value, inline = field
            self.add_field(name=name, value=value, inline=inline)
        else:
            name, value = field
            self.add_field(name=name, value=value, inline=False)

    if kwargs:
        raise TypeError(
            "Embed.__init__ received unexpected keyword arguments: {0}".format(list(kwargs.keys()))
        )


def patch_embed() -> None:
    """Modifies discord.Embed to have new arguments for input."""
    discord.Embed.__init__ = __init__


if __name__ == "__main__":
    e = discord.Embed(
        title="Test title",
        description="test description",
        footer_text="hi",
        fields=[
            ("Field 1", "test"),
            ("Field 2", "more test", True),
            {"name": "test", "value": "data", "inline": True},
        ],
        colour=0xFFF,
    )
    print(e.to_dict())
