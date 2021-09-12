# Addons

Addons are our built-in system to extend the features of the bot in an officially supported manner.

Currently supported systems are plugins, which are slightly modified discord.py extensions.

!!!note
    This guide is for those who want to **write** addons. If you are looking to use an addon, please view our guide [on installing them][installation].


## Guides
- [Installation][installation]
- [Repo Setup](#repo-setup)
- [Making Plugins][making-plugins]


## Repo Setup
In order to be able to install addons, a few things are required.
Each addon type will have its own requirements in addition to the following.

### Overall File Structure
At the base of the addon system is the source. Sources have a folder structure like the following:

```sh
.
├── Plugins/
└── README.md
```

In this structure, this repository is holding addons of a plugin type. The structure of the Plugins folder itself is detailed in the [creating plugins guide][making-plugins].

### Hosting
All addons must be hosted on either github or gitlab as of now.

!!!note
    Addons currently do not automatically update, and need to be re-installed on each run. This will be fixed once the database client exists.

[making-plugins]: ./plugins.md
[installation]: ./installation.md
