from copy import copy

import pytest

from modmail.extensions.plugin_manager import PluginConverter
from modmail.utils.plugins import PLUGINS as GLOBAL_PLUGINS
from modmail.utils.plugins import walk_plugins


# load EXTENSIONS
PLUGINS = copy(GLOBAL_PLUGINS)
PLUGINS.update(walk_plugins())


class TestPluginConverter:
    """Test the extension converter converts extensions properly."""

    all_plugins = {x: y for x, y in walk_plugins()}

    @pytest.fixture(scope="class", name="converter")
    def converter(self) -> PluginConverter:
        """Fixture method for a PluginConverter object."""
        return PluginConverter()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("plugin", [e.rsplit(".", 1)[-1] for e in all_plugins.keys()])
    async def test_conversion_success(self, plugin: str, converter: PluginConverter) -> None:
        """Test all plugins in the list are properly converted."""
        converter.source_list = self.all_plugins
        converted = await converter.convert(None, plugin)

        assert converted.endswith(plugin)
