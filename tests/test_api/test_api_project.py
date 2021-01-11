
import json
import pytest
from datetime import datetime

from .base import PATH, app, user, fetch, get_new_tokens


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
