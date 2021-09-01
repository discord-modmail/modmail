from aiohttp import ClientResponse


class HTTPError(Exception):
    """Response from an http request was not desired."""

    def __init__(self, response: ClientResponse):
        self.response = response
