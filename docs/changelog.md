# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Breaking
- Bot now requires a `RELAY_CHANNEL_ID` configuration variable. (#53)
    - This is where tickets with users will be relayed.
    - At a later point in time, this will be additionally included in a configuration command.

### Added
- docker-compose.yml (#13)
    - Running the bot after configuring the env vars is now as simple as `docker-compose up`
- Automatic docker image creation: `ghcr.io/discord-modmail/modmail` (#19)
- Dockerfile support for all supported hosting providers. (#58)
- Threads system (#53)
    - Messages can now be relayed between a user and a server.
    - NOTE: There is not a database yet, so none of these messages are stored.

### Changed

- Refactored bot creation and bot running (#56)
    - Running the bot is still the same method, but it loads extensions and plugins now.
    - `bot.start()` can also be used if already in a running event loop. Keep in mind using it will require
        handling loop errors, as run() does this automatically.



## [0.1.0] - 2021-08-13

### Added

- Bot modes to determine behavior. Multiple can be applied at once. (#43)
    - `PROD`: the default mode, no dev extensions or dev plugins load
    - `DEVELOP`: the bot developer mode, most useful for people adding features to modmail
- Enables the extension_manager extension.
    - `PLUGIN_DEV`: the plugin developer mode, useful for enabling plugin specific features
    - This is not used yet.
- Extension loading system (#43)
    - scans for extensions in the `modmail/extensions` folder and loads them if they are of the right format.
    - all extensions must be loadable as a module, which means they must have `__init__.py` files in their directories.
- Plugin loading system (#43)
    - scans for plugins in the `modmail/plugins` folder and loads them.
    - Unlike extensions, plugins and their respective folders do not need to have `__init__.py` files and are allowed to be symlinks.
- Extension management commands (#43)
    - load, reload, unload, list, refresh commands for dealing with extensions
    - Run the `ext` command for more details when bot is in `DEVELOP` mode.
- Plugin management commands (#43)
    - load, reload, unload, list, refresh commands for dealing with plugins
    - Run the `plugins` command for more details.
- Extension metadata (#43)
  - used to determine if a cog should load or not depending on the bot mode
- Plugin helper file (#43)
    - `modmail/plugin_helpers.py` contains several helpers for making plugins
        - `PluginCog`
        - `ModmailBot`, imported from `modmail.bot`
        - `ModmailLogger`, imported from `modmail.log`
- Meta Cog (#43)
    - **NOTE**: The commands in this cog are not stabilized yet and should not be relied upon.
    - Prefix command for getting the set prefix. Most useful by mentioning the bot.
    - Uptime command which tells the end user how long the bot has been online.
    - Ping command to see the bot latency.
- Guide on how to contribute to modmail, see \[CONTRIBUTING.md\] <!-- #TODO: Make this a link -->
- Start a Changelog

### Fixed

- Make the bot `http_session` within an event loop.

[0.1.0]: https://github.com/discord-modmail/modmail/releases/tag/v0.1.0
[unreleased]: https://github.com/discord-modmail/modmail/compare/v0.1.0...main
