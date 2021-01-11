
import json
import pytest

from .base import PATH, app, user, fetch, get_new_tokens


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
