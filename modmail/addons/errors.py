class AddonError(Exception):
    """Base Addon utils and extension exception."""

    pass


class NoPluginDirectoryError(AddonError):
    """No plugin directory exists."""

    pass
