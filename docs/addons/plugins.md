# Creating Plugins

If you are looking to write a feature to extend the functionality of your modmail bot, plugins are *the*
supported way to add additional code to modmail.

In short, plugins are discord.py extensions which expand the functionality of the bot beyond its built-in duties.


!!!Tip
    This builds on the [addon structure documentation][addon-guide]. Please ensure you have a solid understanding of the basic repository structure beforehand.

!!!note
    This guide is **not** how to install plugins, please view our [installation guide][installation] for that.

## File Structure Overview

This details the structure of a plugin addon.

```sh
Plugins/
├── react_to_contact
│   ├── listener.py
│   └── react_to_contact.py
├── verify_contact
│   └── verify_contact.py
└── plugin.toml
```

Even though there are three `.py` files, this repository contains two plugins. Each top level folder in the Plugins folder contains one plugin.
The number of py files in each plugins folder does not matter, there are still two plugins here.

One plugin here is named `react_to_contact`, the other is `verify_contact`

However, those are not user friendly names. It would be a lot easier for the end user to reference with `React to Contact`, and for the user interface to refer to it as such.

To do so, a name can be provided in the plugin.toml file.

## plugin.toml

There are several variables which can be configured by providing a plugin.toml file.

If you don't already know what toml is, [check out their docs](https://toml.io/)

!!!tip
    `plugin.toml` is supplemental to the list of folders. This means that all plugins in the repository are installable at any time. Providing a plugin.toml does not mean that any plugins *not* in the toml are not included anymore.

    This has the advantage of being able to use `plugin.toml` to change the name of one plugin, without having to add all other plugins to the toml.


### Options

A full `plugin.toml` for the above repository may look like this:

```toml
[[plugins]]
name = 'React to Contact'
description = 'Provides a permanent message where the user can react to open a thread'
directory = 'react_to_contact'

[[plugins]]
name = 'Verify Contact'
description = 'Prevents the user from accidently opening a thread by asking if they are sure.'
directory = 'verify_contact'
```

The name and directory are the only keys in use today,
the description is not yet used.

The `directory` key is required, if wanting to set any other settings for a plugin.

!!!tip
    `directory` is aliased to `folder`. Both keys are valid, but if the `directory` key exists it will be used and `folder` will be ignored.

Name is optional, and defaults to the directory if not provided.

!!!warning
    Capitals matter. Both the `plugin.toml` file and `[[plugins]]` table ***must*** be lowercase.
    This also goes for all keys and directory arguments--they must match the capitials of the existing directory.

### Dependencies

If the dependencies that the bot is installed with, it is possible to declare a dependency and it will be installed when installing the plugin.

!!! Waring
    For the most part, you won't need to use this. But if you absolutely must use an additional dependency which isn't part of the bot, put it in this array.

This is an array of arguments which should be just like they are being passed to pip.

```toml
[[plugins]]
directory = 'solar_system'
dependencies = ['earthlib==0.2.2']
```

This will install earthlib 0.2.2.

## Code

Now that we have an understanding of where the plugin files go, and how to configure them, its time to write their code.

### `PluginCog`

All plugin cogs ***must*** inherit from `PluginCog`.

If plugin cogs do not inherit from this class, they will fail to load.

A majority of the needed modmail classes have been imported into helpers for your convinence.

```python
from modmail.addons import helpers

# Cog
helpers.PluginCog

# Extension Metadata
helpers.ExtMetadata

### For Typehints
# bot class
helpers.ModmailBot

# logger
helpers.ModmailLogger
```

### `ExtMetadata`

There is a system where extensions can declare load modes.

There is a longer write up on it [here][ext_metadata].

[addon-guide]: ./README.md
[ext_metadata]: /contributing/creating_an_extension/#bot_mode-and-extmetadata
[installation]: ./installation.md#plugins
