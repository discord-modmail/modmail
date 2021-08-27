import discord
import pytest
from discord import Colour

from modmail.utils.embeds import patch_embed


@pytest.mark.dependency(name="patch_embed")
def test_patch_embed():
    """Ensure that the function changes init only after the patch is called."""
    from modmail.utils.embeds import __init__ as init
    from modmail.utils.embeds import original_init

    assert discord.Embed.__init__ == original_init
    patch_embed()
    assert discord.Embed.__init__ == init


@pytest.mark.dependency(depends_on="patch_embed")
def test_create_embed():
    """Test creating an embed with patched parameters works properly."""
    title = "Test title"
    description = "Test description"
    footer_text = "Test footer text"
    color = 0xFFF
    e = discord.Embed(
        title=title,
        description=description,
        footer_text=footer_text,
        fields=[
            ("Field 1", "test"),
            ("Field 2", "more test", True),
            {"name": "test", "value": "data", "inline": True},
        ],
        colour=color,
    )
    assert e.to_dict() == {
        "footer": {"text": footer_text},
        "fields": [
            {"inline": False, "name": "Field 1", "value": "test"},
            {"inline": True, "name": "Field 2", "value": "more test"},
            {"inline": True, "name": "test", "value": "data"},
        ],
        "color": 4095,
        "type": "rich",
        "description": description,
        "title": title,
    }


@pytest.mark.dependency(depends_on="patch_embed")
def test_create_embed_with_extra_params():
    """Test creating an embed with extra parameters errors properly."""
    with pytest.raises(TypeError, match="ooga_booga"):
        discord.Embed("hello", ooga_booga=3)


@pytest.mark.dependency(depends_on="patch_embed")
def test_create_embed_with_description_and_content():
    """
    Create an embed while providing both description and content parameters.

    Providing both is ambiguous and should error.
    """
    with pytest.raises(
        TypeError, match="Description and content are aliases for the same field, but both were provided."
    ):
        discord.Embed(description="hello", content="goodbye")
