
import sys
import json
import os.path
from urllib.parse import urljoin, urlencode
from datetime import datetime
from time import mktime
from uuid import uuid4

import tornado.ioloop
import pytest
from tornado.httputil import url_concat

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from db_manage import create_user, delete_user
from server.app import ServerApp, get_db_pool

URI = {
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


async def fetch(http_client, base_url, uri, method='POST', params=None):
    parameters = {'method': method, 'raise_error': False}
    if method == 'GET':
        parameters['request'] = url_concat(urljoin(base_url, uri), params)
    elif method == 'POST':
        parameters['request'] = urljoin(base_url, uri)
        parameters['body'] = urlencode(params)
    return await http_client.fetch(**parameters)


async def get_new_tokens(http_client, base_url, user):
    r = await fetch(http_client, base_url, URI['new_tokens'], 'POST', user)
    data = json.loads(r.body)
    return {k: data[k] for k in ('token_select', 'token_verify')}


@pytest.fixture
def user():
    username = 'user_{}'.format(int(mktime(datetime.utcnow().timetuple())))
    user_dict = {
        'username': username,
        'password': create_user(username, generate_password=True)
    }
    yield user_dict
    delete_user(username)


@pytest.fixture
def app():
    loop = tornado.ioloop.IOLoop.current()
    db_pool = loop.asyncio_loop.run_until_complete(get_db_pool())
    return ServerApp(loop.asyncio_loop, db_pool)


@pytest.mark.gen_test
async def test_tokens_new(http_client, base_url, user):
    # Valid username and password
    r = await fetch(http_client, base_url, URI['new_tokens'], 'POST', user)
    assert r.code == 200

    # Valid username and invalid password
    password = user['password']
    user['password'] = uuid4().hex
    r = await fetch(http_client, base_url, URI['new_tokens'], 'POST', user)
    assert r.code == 403

    # Delete user and try to get new tokens again
    # Invalid username and invalid password
    user['password'] = password
    delete_user(user['username'])
    r = await fetch(http_client, base_url, URI['new_tokens'], 'POST', user)
    assert r.code == 403


@pytest.mark.gen_test
async def test_tokens_renew(http_client, base_url, user):
    r = await fetch(http_client, base_url, URI['new_tokens'], 'POST', user)
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Valid renew token
    r = await fetch(http_client, base_url, URI['renew_tokens'], 'POST', tokens)
    assert r.code == 200
    tokens_outdated = tokens
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Try to use outdated tokens
    r = await fetch(http_client, base_url, URI['renew_tokens'], 'POST',
                    tokens_outdated)
    assert r.code == 403

    # Invalid renew token for valid select token and verify tokens
    tokens_invalid_renew = tokens.copy()
    tokens_invalid_renew['token_renew'] = uuid4().hex
    r = await fetch(http_client, base_url, URI['renew_tokens'], 'POST',
                    tokens_invalid_renew)
    assert r.code == 403

    # Delete user and try to renew tokens again
    delete_user(user['username'])
    r = await fetch(http_client, base_url, URI['renew_tokens'], 'POST', tokens)
    assert r.code == 403


@pytest.mark.gen_test
async def test_project_list(http_client, base_url, user):
    tokens = await get_new_tokens(http_client, base_url, user)
    r = await fetch(http_client, base_url, URI['project_base'], 'GET', tokens)
    assert r.code == 200
    data = json.loads(r.body)
    assert len(data['projects']) == 1
    keys = list(data['projects'][0].keys())
    assert keys == ['id', 'role', 'title', 'description']
