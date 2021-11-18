import aiohttp
import pytest


@pytest.fixture
@pytest.mark.asyncio
async def http_session() -> aiohttp.ClientSession:
    """Fixture function for a aiohttp.ClientSession."""
    resolver = aiohttp.AsyncResolver()
    connector = aiohttp.TCPConnector(resolver=resolver)
    client_session = aiohttp.ClientSession(connector=connector)

    yield client_session

    await client_session.close()
    await connector.close()
    await resolver.close()
