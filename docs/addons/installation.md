# Installation

!!!note
    If you are looking to write addons, check our [writing addons][addon-guide] guide.



## Plugins

Plugins are discord.py extensions which expand the functionality of the bot beyond its core feature: relaying messages back and forth between staff and members.

We've done our best to make this system easy to use for both novice and experienced developers--installing plugins should require no programming knowledge at all.

By default, modmail will install plugins hosted on [github.com](https://github.com), but also supports installing from github.

This may look complex, but it supports a wide variety of options.

```fix
?plugin install [git-host] <user>/<repo> <name> [@ref]
?plugin install <link> <name> [@ref]
```


### Git-host (Optional)
Valid options are:

- `github`
- `gitlab`

Default:

- `github`


### User/Repo

This is the user and the respository hosted on a valid git-host.

In the link <https://github.com/discord-modmail/addons>, the user and repo are `discord-modmail/addons`.


### Name

This is the addon name, it is not allowed to contain `@`.
By default, this is the plugin folder name, unless it is defined in the plugin.toml file.
A repository should provide a list of their plugins either in a plugin readme, or the full repository readme.


### Ref

This is the git reference, leave blank to use the repository default.
If you would like to use a specific commit, branch, or tag, then provide it preceeded by a `@`.
For example, to use tagged version 1.2, `@v1.2` would install from that tag.

[addon-guide]: ./README.md
