
import json
from urllib.parse import urljoin, urlencode
from uuid import uuid4

import tornado.ioloop
import keyring
import pytest

from server.app import ServerApp, get_db_pool

USERNAME = 'oleg'
PASSWORD = keyring.get_password('tasker-dev', USERNAME)


async def get_tokens(http_client, base_url, password=None):
    data = {'username': USERNAME, 'password': PASSWORD}
    if password is not None:
        data['password'] = password
    return await http_client.fetch(
        urljoin(base_url, '/api/tokens/new'),
        method='POST',
        body=urlencode(data),
        raise_error=False
    )


@pytest.fixture
def app():
    loop = tornado.ioloop.IOLoop.current()
    db_pool = loop.asyncio_loop.run_until_complete(get_db_pool())
    return ServerApp(loop.asyncio_loop, db_pool)


@pytest.mark.gen_test
async def test_api_tokens_get(http_client, base_url):
    # Valid username and password
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/new'),
        method='POST',
        body=urlencode({'username': USERNAME, 'password': PASSWORD})
    )
    assert r.code == 200

    # Invalid password
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/new'),
        method='POST',
        body=urlencode({'username': USERNAME, 'password': 'PASSWORD'}),
        raise_error=False
    )
    assert r.code == 403


@pytest.mark.gen_test
async def test_api_tokens_renew(http_client, base_url):
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/new'),
        method='POST',
        body=urlencode({'username': USERNAME, 'password': PASSWORD})
    )
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Invalid renew token
    tokens_invalid = tokens.copy()
    tokens_invalid['token_renew'] = uuid4().hex
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/renew'),
        method='POST',
        body=urlencode(tokens_invalid),
        raise_error=False
    )
    assert r.code == 403

    # Valid renew token
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/renew'),
        method='POST',
        body=urlencode(tokens)
    )
    assert r.code == 200

    # Try to use outdated tokens
    r = await http_client.fetch(
        urljoin(base_url, '/api/tokens/renew'),
        method='POST',
        body=urlencode(tokens),
        raise_error=False
    )
    assert r.code == 403
