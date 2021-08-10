# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Bot modes to determine behavior.
  - `PROD`, `DEVELOP`, `PLUGIN_DEV`
- Extension loading system
  - scans for extensions in the `modmail/extensions` folder and loads them if they are of the right format.
- Plugin loading system
  - scans for plugins in the plugins folder and loads them.
- Extension management commands
  - Run the `ext` command for more details when bot is in `DEVELOP` mode.
- Plugin management commands
- - Run the `plugins` command for more details.
- Extension metadata
  - used to determine if a cog should load or not depending on the bot mode
- Guide on how to contribute to modmail, see [CONTRIBUTING.md](./CONTRIBUTING.md)

[unreleased]: https://github.com/discord-modmail/modmail/compare/main
