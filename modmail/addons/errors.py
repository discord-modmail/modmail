class AddonError(Exception):
    """Base Addon utils and extension exception."""

    pass


class PluginError(AddonError):
    """General Plugin error."""

    pass


class NoPluginDirectoryError(PluginError):
    """No plugin directory exists."""

    pass


class PluginNotFoundError(PluginError):
    """Plugins are not found and can therefore not be actioned on."""

    pass


class NoPluginTomlFoundError(PluginError):
    """Raised when a plugin.toml file is expected to exist but does not exist."""
