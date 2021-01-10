
import json
from urllib.parse import urljoin, urlencode
from uuid import uuid4

import tornado.ioloop
import pytest

from db_manage import create_user, delete_user
from server.app import ServerApp, get_db_pool

USERNAMES = [uuid4().hex for i in range(3)]
USERS = [
    {'username': u, 'password': create_user(u, generate_password=True)}
    for u in USERNAMES
]
ENDPOINTS = {
    'new_tokens': '/api/tokens/new',
    'renew_tokens': '/api/tokens/renew',
    'project_base': '/api/project',
    'project': '/api/project/{}',
    'folder_project': '/api/folder/{}',
    'folder': '/api/folder/{}/{}',
    'task_project': '/api/project/{}',
    'task_folder': '/api/task/{}/{}',
    'task': '/api/task/{}/{}/{}'
}


@pytest.fixture
def app():
    loop = tornado.ioloop.IOLoop.current()
    db_pool = loop.asyncio_loop.run_until_complete(get_db_pool())
    return ServerApp(loop.asyncio_loop, db_pool)


@pytest.mark.gen_test
async def test_api_tokens_new(http_client, base_url):
    user = USERS[2].copy()
    # Valid username and password
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['new_tokens']),
        method='POST',
        body=urlencode(user)
    )
    assert r.code == 200

    # Valid username and invalid password
    user['password'] = uuid4().hex
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['new_tokens']),
        method='POST',
        body=urlencode(user),
        raise_error=False
    )
    assert r.code == 403

    # Delete user and try get new tokens again
    # Invalid username and invalid password
    user = USERS[2]
    delete_user(user['username'])
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['new_tokens']),
        method='POST',
        body=urlencode(user),
        raise_error=False
    )
    assert r.code == 403


@pytest.mark.gen_test
async def test_api_tokens_renew(http_client, base_url):
    user = USERS[1]
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['new_tokens']),
        method='POST',
        body=urlencode(user)
    )
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Invalid renew token
    tokens_invalid = tokens.copy()
    tokens_invalid['token_renew'] = uuid4().hex
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['renew_tokens']),
        method='POST',
        body=urlencode(tokens_invalid),
        raise_error=False
    )
    assert r.code == 403

    # Valid renew token
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['renew_tokens']),
        method='POST',
        body=urlencode(tokens)
    )
    assert r.code == 200
    tokens_outdated = tokens
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Try to use outdated tokens
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['renew_tokens']),
        method='POST',
        body=urlencode(tokens_outdated),
        raise_error=False
    )
    assert r.code == 403

    # Delete user and try to renew tokens again
    delete_user(user['username'])
    r = await http_client.fetch(
        urljoin(base_url, ENDPOINTS['renew_tokens']),
        method='POST',
        body=urlencode(tokens),
        raise_error=False
    )
    assert r.code == 403
