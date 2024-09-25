class MissingAttributeError(Exception):
    """Missing attribute."""

    pass


class InvalidArgumentError(Exception):
    """Improper argument."""

    pass


class ConfigLoadError(Exception):
    """Exception if the configuration failed to load from a local file."""

    pass
