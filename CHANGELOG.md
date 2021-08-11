# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0]

### Added

- Bot modes to determine behavior. Multiple can be applied at once.
  - `PROD`: the default mode, no dev extensions or dev plugins load
  - `DEVELOP`: the bot developer mode, most useful for people adding features to modmail
    - Enables the extension_manager extension.
  - `PLUGIN_DEV`: the plugin developer mode, useful for enabling plugin specific features
    - This is not used yet.
- Extension loading system
  - scans for extensions in the `modmail/extensions` folder and loads them if they are of the right format.
- Plugin loading system
  - scans for plugins in the `modmail/plugins` folder and loads them.
- Extension management commands
  - load, reload, unload, list, refresh commands for dealing with extensions
  - Run the `ext` command for more details when bot is in `DEVELOP` mode.
- Plugin management commands
  - load, reload, unload, list, refresh commands for dealing with plugins
- - Run the `plugins` command for more details.
- Extension metadata
  - used to determine if a cog should load or not depending on the bot mode
- Plugin helper file
  - `modmail/plugin_helpers.py` contains several helpers for making plugins
    - `PluginCog`
    - `ModmailBot`, imported from `modmail.bot`
    - `ModmailLogger`, imported from `modmail.log`
- Meta Cog
  - **NOTE**: The commands in this cog are not stabilized yet and should not be relied upon.
  - Prefix command for getting the set prefix. Most useful by mentioning the bot.
  - Uptime command which tells the end user how long the bot has been online.
  - Ping command to see the bot latency.
- Guide on how to contribute to modmail, see [CONTRIBUTING.md](./CONTRIBUTING.md)
- Start a Changelog

### Fixed

- Make the bot http_session within an event loop.

[0.1.0]: https://github.com/discord-modmail/modmail/releases/tag/v0.1.0
[unreleased]: https://github.com/discord-modmail/modmail/compare/v0.1.0...main
