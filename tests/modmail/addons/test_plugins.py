from __future__ import annotations

import pytest

from modmail.addons.models import Plugin
from modmail.addons.plugins import parse_plugin_toml_from_string

VALID_PLUGIN_TOML = """
[[plugins]]
name = "Planet"
folder = "planet"
description = "Planet. Tells you which planet you are probably on."
min_bot_version = "v0.2.0"
"""


@pytest.mark.parametrize(
    "toml, name, folder, description, min_bot_version",
    [
        (
            VALID_PLUGIN_TOML,
            "Planet",
            "planet",
            "Planet. Tells you which planet you are probably on.",
            "v0.2.0",
        )
    ],
)
def test_parse_plugin_toml_from_string(
    toml: str, name: str, folder: str, description: str, min_bot_version: str
) -> None:
    """Make sure that a plugin toml file is correctly parsed."""
    plugs = parse_plugin_toml_from_string(VALID_PLUGIN_TOML)
    plug = plugs[0]
    print(plug.__repr__())
    assert isinstance(plug, Plugin)
    assert plug.name == name
    assert plug.folder == folder
    assert plug.description == description
