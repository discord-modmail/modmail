from copy import copy

import pytest

from modmail.extensions.plugin_manager import PluginConverter
from modmail.utils.plugins import PLUGINS, walk_plugins


# load EXTENSIONS
PLUGINS = copy(PLUGINS)
PLUGINS.update(walk_plugins())


class TestExtensionConverter:
    """Test the extension converter converts extensions properly."""

    @pytest.fixture(scope="class", name="converter")
    def converter(self) -> PluginConverter:
        """Fixture method for a ExtensionConverter object."""
        return PluginConverter()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("extension", [e.rsplit(".", 1)[-1] for e in PLUGINS.keys()])
    async def test_conversion_success(self, extension: str, converter: PluginConverter) -> None:
        """Test all extensions in the list are properly converted."""
        converter.source_list = PLUGINS
        converted = await converter.convert(None, extension)

        assert converted.endswith(extension)
