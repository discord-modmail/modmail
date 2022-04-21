# Creating an Extension

Welcome!

Please note that extensions are cogs are different things. Extensions are files which add features to the bot,
and a cog is way to group commands and features within a file.

This is an addendum to the [discord.py guide](https://discordpy.readthedocs.io/en/master/ext/commands/extensions.html) on how to write extensions.
This guide below details additional information which is not part of discord.py.

**There is one major change from discord.py**:
Cogs **must** inherit from `ModmailCog`.
If this does not happen, the bot will let you know.

ModmailCog is defined in `modmail/utils/cogs.py`.

## BOT_MODE and `ExtMetadata`

In general, an extension does not need to use the feature of an extension metadata.

On every extension of the bot, an `EXT_METADATA` constant should exist, and it should be an instance of `ExtMetadata`.
The `ExtMetadata` class is defined in `modmail/utils/cogs.py`, along with `BotModeEnum`.

It should be sufficent to have an EXT_METADATA variable declared at the top of the file as an instance of ExtMetadata.

```python
from modmail.utils.cogs import ExtMetadata

EXT_METADATA = ExtMetadata()
```

### `ExtMetadata`

The purpose of ExtMetadata is to define metadata about an extension. Currently, it supports two items of metadata.

- `load_if_mode`
    - used to determine if this extension should be loaded at runtime.
- `no_unload` (Not supported by plugins)
    - prevents an extension from being unloaded by the `?ext unload` command. This is mainly used to keep the extension manager from unloading itself.

`no_unload` is pretty self explanatory, pass either True or False and the extension will either be blocked from being unloaded, or allowed to unload.
This only has an impact if the current bot mode is DEVELOP. Note that this does prevent the developer from *reloading* the extension.

### `load_if_mode`

`load_if_mode` currently has three modes, which each have their own uses.:

- `PRODUCTION`
    - The default mode, the bot is always in this mode.
- `DEVELOP`
    - Bot developer. Enables the extension management commands.
- `PLUGIN_DEV`
    - Plugin developer. Enables lower-level plugin commands.

!!!tip
    To enable these modes, set the corresponding environment variable to a truthy value. eg `DEVELOP=1` in your project `.env` file will enable the bot developer mode.

To set an extension to only load on one cog, set the load_if_mode param when initialising a ExtMetadata object.

```python
from modmail.utils.cogs import BotModeEnum, ExtMetadata

EXT_METADATA = ExtMetadata(load_if_mode=BotModeEnum.DEVELOP)
```

*This is not a complete extension and will not run if tested!*

This `EXT_METADATA` variable above declares the extension will only run if a bot developer is running the bot.

However, we may want to load our extension normally but have a command or two which only load in specific modes.

### `BOT_MODE`

The bot exposes a BOT_MODE variable which contains a bitmask of the current mode. This is created with the BotModeEnum.
This allows code like this to determine if the bot mode is a specific mode.

```python
from modmail.utils.cogs import BOT_MODE, BotModeEnum

is_plugin_dev_enabled = BOT_MODE & BotModeEnum.PLUGIN_DEV
```

This is used in the plugin_manager extension to determine if the lower-level commands which manage plugin extensions directly should be enabled.
