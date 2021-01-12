
import json
from urllib.parse import urljoin, urlencode
from datetime import datetime
from time import mktime

import tornado.ioloop
import pytest
from tornado.httputil import url_concat

from db_manage import create_user, delete_user
from server.app import ServerApp, get_db_pool

PATH = {
    'new_tokens': '/api/tokens/new',
    'renew_tokens': '/api/tokens/renew',
    'project_base': '/api/project',
    'project': '/api/project/{}',
    'folder_project': '/api/folder/{}',
    'folder': '/api/folder/{}/{}',
    'task_project': '/api/task/{}',
    'task_folder': '/api/task/{}/{}',
    'task': '/api/task/{}/{}/{}'
}


async def fetch(http_client, base_url, path, method, params=None):
    parameters = {'method': method, 'raise_error': False}
    if method in ('GET', 'DELETE'):
        parameters['request'] = url_concat(urljoin(base_url, path), params)
    elif method == 'POST':
        parameters['request'] = urljoin(base_url, path)
        parameters['body'] = urlencode(params)
    elif method == 'PUT':
        parameters['request'] = url_concat(urljoin(base_url, path), params)
        # Workaround `ValueError: Body must not be None for method PUT`
        parameters['body'] = ''
    return await http_client.fetch(**parameters)


async def get_new_tokens(http_client, base_url, user):
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', user)
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
