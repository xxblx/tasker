
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

PATH = {
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


@pytest.mark.gen_test
async def test_tokens_new(http_client, base_url, user):
    # Valid username and password
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', user)
    assert r.code == 200

    # Valid username and invalid password
    password = user['password']
    user['password'] = uuid4().hex
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', user)
    assert r.code == 403

    # Delete user and try to get new tokens again
    # Invalid username and invalid password
    user['password'] = password
    delete_user(user['username'])
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', user)
    assert r.code == 403


@pytest.mark.gen_test
async def test_tokens_renew(http_client, base_url, user):
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', user)
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Valid renew token
    r = await fetch(http_client, base_url, PATH['renew_tokens'], 'POST', tokens)
    assert r.code == 200
    tokens_outdated = tokens
    tokens = json.loads(r.body)
    del tokens['expires_in']

    # Try to use outdated tokens
    r = await fetch(http_client, base_url, PATH['renew_tokens'], 'POST',
                    tokens_outdated)
    assert r.code == 403

    # Invalid renew token for valid select token and verify tokens
    tokens_invalid_renew = tokens.copy()
    tokens_invalid_renew['token_renew'] = uuid4().hex
    r = await fetch(http_client, base_url, PATH['renew_tokens'], 'POST',
                    tokens_invalid_renew)
    assert r.code == 403

    # Delete user and try to renew tokens again
    delete_user(user['username'])
    r = await fetch(http_client, base_url, PATH['renew_tokens'], 'POST', tokens)
    assert r.code == 403


@pytest.mark.gen_test
async def test_project_get(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)

    # List available projects
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'projects' in data
    # There should be only one project for a new user
    assert len(data['projects']) == 1
    projects_keys = ['id', 'role', 'title', 'description']
    assert list(data['projects'][0].keys()) == projects_keys
    project_id = data['projects'][0]['id']

    # Get project details by id
    r = await fetch(http_client, base_url, PATH['project'].format(project_id),
                    'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert list(data.keys()) == ['id', 'title', 'description', 'users']
    assert len(data['users']) == 1
    assert list(data['users'][0].keys()) == ['username', 'role']
    assert data['users'][0]['username'] == user['username']

    # Try to get non-existent project
    r = await fetch(http_client, base_url, PATH['project'].format(-1),
                    'GET', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_project_add(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    # Try to add a project without necessary parameters
    r = await fetch(http_client, base_url, PATH['project_base'], 'POST', params)
    assert r.code == 400

    # Add a project with title (mandatory) and description (optional)
    params['title'] = 'New project'
    description = 'Description {}'.format(datetime.now())
    params['description'] = description
    r = await fetch(http_client, base_url, PATH['project_base'], 'POST', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'id' in data

    # Get the project by id and compare
    params = {k: params[k] for k in ('token_select', 'token_verify')}
    r = await fetch(http_client, base_url, PATH['project'].format(data['id']),
                    'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert data['title'] == 'New project'
    assert data['description'] == description


@pytest.mark.gen_test
async def test_project_delete(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    params_add = params.copy()
    params_add.update({'title': 'project'})
    r = await fetch(http_client, base_url, PATH['project_base'], 'POST',
                    params_add)
    project_id = json.loads(r.body)['id']

    # Delete project
    r = await fetch(http_client, base_url, PATH['project'].format(project_id),
                    'DELETE', params)
    assert r.code == 200
    # Request deleted project
    r = await fetch(http_client, base_url, PATH['project'].format(project_id),
                    'GET', params)
    assert r.code == 404
    # Try to delete non-existent project
    r = await fetch(http_client, base_url, PATH['project'].format(-1),
                    'DELETE', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_folder_get(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    project_id = json.loads(r.body)['projects'][0]['id']
    # List folders in project
    r = await fetch(http_client, base_url,
                    PATH['folder_project'].format(project_id), 'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'folders' in data
    assert list(data['folders'][0].keys()) == ['id', 'title']
    # Try get folders of non-existent project
    r = await fetch(http_client, base_url, PATH['folder_project'].format(-1),
                    'GET', params)
    assert r.code == 404

    # Get folder details by id
    folder_id = data['folders'][0]['id']
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, folder_id), 'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert list(data.keys()) == ['id', 'title']
    # Try to get non-existent folder by valid project id
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, -1), 'GET', params)
    assert r.code == 404
    # Try to get non-existent folder of non-existent project
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(-1, -1), 'GET', params)
    assert r.code == 404

@pytest.mark.gen_test
async def test_folder_add(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    # Add folder
    project_id = json.loads(r.body)['projects'][0]['id']
    params['title'] = 'New folder'
    r = await fetch(http_client, base_url,
                    PATH['folder_project'].format(project_id), 'POST', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'id' in data
    # Try to add a folder to non-existent project
    r = await fetch(http_client, base_url,
                    PATH['folder_project'].format(-1), 'POST', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_folder_delete(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    project_id = json.loads(r.body)['projects'][0]['id']
    params['title'] = 'New folder'
    r = await fetch(http_client, base_url,
                    PATH['folder_project'].format(project_id), 'POST', params)
    del params['title']
    folder_id = json.loads(r.body)['id']
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, folder_id), 'DELETE',
                    params)
    assert r.code == 200

    # Try to delete non-existent folder by valid project id
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, -1), 'DELETE', params)
    assert r.code == 404
    # Try to delete non-existent folder of non-existent project
    r = await fetch(http_client, base_url, PATH['folder'].format(-1, -1),
                    'DELETE', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_folder_update(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user)
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    project_id = json.loads(r.body)['projects'][0]['id']
    params['title'] = 'New folder'
    r = await fetch(http_client, base_url,
                    PATH['folder_project'].format(project_id), 'POST', params)
    folder_id = json.loads(r.body)['id']

    params['title'] = 'Updated folder'
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, folder_id), 'PUT', params)
    assert r.code == 200
    del params['title']
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, folder_id), 'GET', params)
    data = json.loads(r.body)
    assert data['title'] == 'Updated folder'

    # Try without mandatory parameter - title
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, folder_id), 'PUT', params)
    assert r.code == 400
    # Try to update non-existent folder by valid project id
    params['title'] = 'Updated folder'
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(project_id, -1), 'PUT', params)
    assert r.code == 404
    # Try to update non-existent folder of non-existent project
    params['title'] = 'Updated folder'
    r = await fetch(http_client, base_url,
                    PATH['folder'].format(-1, -1), 'PUT', params)
    assert r.code == 404
