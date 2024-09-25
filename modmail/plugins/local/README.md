# Plugins

This folder is where local plugins can be put for developing.

Plugins should be like normal discord cogs, but should subclass `PluginCog` from `modmail.plugin_helpers`

```py
from modmail.plugin_helpers import PluginCog


class MyPlugin(PluginCog):
    pass
```
