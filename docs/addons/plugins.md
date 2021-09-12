# Creating Plugins

## File Structure Overview

This details the structure of a plugin addon.
!!!note
    This builds on the [addon structure documentation][addon-guide].

!!!note
    This guide is **not** how to install plugins, please view our [installation guide][installation] for that.
```sh
Plugins/
├── react_to_contact
│   ├── listener.py
│   └── react_to_contact.py
├── verify_contact
│   └── verify_contact.py
└── plugin.toml
```

Even though there are three .py files, this repository contains two plugins. Each top level folder in the Plugins folder contains one plugin.
The number of py files in each plugins folder does not matter, there are still two plugins here.

One plugin here is named `react_to_contact`, the other is `verify_contact`

However, those are not user friendly names. It would be a lot easier for the end user to reference with `React to Contact`, and for the user interface to refer to it as such.

To do so, a name can be provided in the plugin.toml file.

## plugin.toml

There are several variables which can be configured by providing a plugin.toml file.

If you don't already know what toml is, [check out their docs](https://toml.io/)


!!!warning
    `plugin.toml` is supplemental to the list of folders. This means that all plugins in the repository are installable at any time. Providing a plugin.toml does not mean that any plugins *not* in the toml are not included anymore.

    This has the advantage of being able to use `plugin.toml` to change the name of one plugin, without having to add all other plugins to the toml.


A full plugin.toml for the above repository may look like this:

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
`directory` is required, name is optional, and defaults to the directory if not provided.




[addon-guide]: ./README.md
[addon-repo-structure]: ./README.md#initial-setup
[installation]: ./installation.md#plugins
