from aiohttp import ClientResponse


class HTTPError(Exception):
    """Response from an http request was not desired."""

    def __init__(self, response: ClientResponse):
        self.response = response


class MissingAttributeError(Exception):
    """Missing attribute."""

    pass


class InvalidArgumentError(Exception):
    """Improper argument."""

    pass


class ConfigLoadError(Exception):
    """Exception if the configuration failed to load from a local file."""

    pass
