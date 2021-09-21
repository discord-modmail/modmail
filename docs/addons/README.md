# Addons

Addons are our built-in system to extend the features of the bot in an officially supported manner.

Modmail, in its most basic form, is simple: relay messages to and from users to staff members.
However, we acknowledge that its not a one-size-fits-all solution.
Some communities need a few more features than others.
That's where the addon system fills the void.

The addon system currently supports only one kind of addon, plugins.
This guide will help you set up a respository to create your own addons.
Once its set up, please refer to the [plugin creation guide][making-plugins] for more details.

!!!note
    This guide is for those who want to **write** addons. If you are looking to use an addon, please view our guide [on installing them][installation].

## Guides

- [Installation]
- [Repo Setup](#repo-setup)
- [Creating Plugins][making-plugins]

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

[installation]: ./installation.md
[making-plugins]: ./plugins.md
