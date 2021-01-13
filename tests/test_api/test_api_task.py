
import json
import pytest
import asyncio
from time import mktime
from datetime import datetime, timedelta

from .base import PATH, app, user, fetch, get_new_tokens


def check_task_dict(task):
    res = []
    for key in task.keys():
        val = task[key]
        if val is None:
            if key in ['description', 'datetime_from', 'datetime_due']:
                continue
            else:
                raise Exception('{} is not supposed to be None'.format(key))
        if key in ('title', 'description', 'username'):
            res.append(isinstance(task[key], str))
        else:
            res.append(isinstance(task[key], int))
    return all(res)


@pytest.mark.gen_test
async def test_task_get(http_client, base_url, user):
    params = await get_new_tokens(http_client, base_url, user['password_auth'])
    r = await fetch(http_client, base_url, PATH['project_base'], 'GET', params)
    project_id = json.loads(r.body)['projects'][0]['id']

    # Tasks by project
    task_keys = ['project_id', 'folder_id', 'id', 'title', 'datetime_from',
                 'datetime_due', 'edited']
    r = await fetch(http_client, base_url,
                    PATH['task_project'].format(project_id), 'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'tasks' in data
    assert sorted(list(data['tasks'][0].keys())) == sorted(task_keys)
    assert check_task_dict(data['tasks'][0]) is True
    folder_id = data['tasks'][0]['folder_id']
    task_id = data['tasks'][0]['id']
    # Invalid id
    r = await fetch(http_client, base_url, PATH['task_project'].format(0),
                    'GET', params)
    assert r.code == 404

    # Tasks by project and folder
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'tasks' in data
    assert sorted(list(data['tasks'][0].keys())) == sorted(task_keys)
    assert check_task_dict(data['tasks'][0]) is True
    # Invalid ids
    r = await fetch(http_client, base_url, PATH['task_folder'].format(0, 0),
                    'GET', params)
    assert r.code == 404

    # Task by id
    task_keys = ['id', 'project_id', 'folder_id', 'title', 'description',
                 'datetime_from', 'datetime_due', 'created', 'edited',
                 'username']
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'GET', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert sorted(list(data.keys())) == sorted(task_keys)
    assert check_task_dict(data) is True
    # Invalid ids
    r = await fetch(http_client, base_url, PATH['task'].format(0, 0, 0),
                    'GET', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_task_add(http_client, base_url, user):
    project_id, folder_id = user['project_id'], user['folder_id']
    params = await get_new_tokens(http_client, base_url, user['password_auth'])

    # Try to add without mandatory params
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    assert r.code == 400

    # Mandatory params
    params['title'] = 'New task {}'.format(datetime.now())
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    assert r.code == 200

    # Optional params
    params['description'] = 'Description {}'.format(datetime.now())
    datetime_from = datetime.utcnow()
    datetime_due = datetime.now() + timedelta(days=3)
    params['datetime_from'] = int(mktime(datetime_from.timetuple()))
    params['datetime_due'] = int(mktime(datetime_due.utctimetuple()))
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    assert r.code == 200
    data = json.loads(r.body)
    assert 'id' in data
    task_id = data['id']

    tokens = {k: params[k] for k in ('token_select', 'token_verify')}
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'GET', tokens)
    data = json.loads(r.body)
    for k in ('title', 'description', 'datetime_from', 'datetime_due'):
        assert data[k] == params[k]
    assert data['id'] == task_id
    assert data['project_id'] == project_id
    assert data['folder_id'] == folder_id

    # Invalid timestamp
    params['datetime_from'] = 'oops, this is not a timestamp'
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    assert r.code == 400


@pytest.mark.gen_test
async def test_task_delete(http_client, base_url, user):
    project_id, folder_id = user['project_id'], user['folder_id']
    params = await get_new_tokens(http_client, base_url, user['password_auth'])
    params['title'] = 'New task'
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    task_id = json.loads(r.body)['id']

    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'DELETE', params)
    assert r.code == 200
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'GET', params)
    assert r.code == 404


@pytest.mark.gen_test
async def test_task_update(http_client, base_url, user):
    project_id, folder_id = user['project_id'], user['folder_id']
    params = await get_new_tokens(http_client, base_url, user['password_auth'])
    params['title'] = 'New task'
    r = await fetch(http_client, base_url,
                    PATH['task_folder'].format(project_id, folder_id),
                    'POST', params)
    task_id = json.loads(r.body)['id']
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'GET', params)
    edited = json.loads(r.body)['edited']
    # Make sure timestamp of upcoming PUT request will be greater than now
    await asyncio.sleep(1)

    # Try without mandatory parameter
    del params['title']
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'PUT', params)
    assert r.code == 400

    params['title'] = 'Task {}'.format(datetime.now())
    # Optional parameters
    params['description'] = 'Description {}'.format(datetime.now())
    datetime_from = datetime.utcnow()
    datetime_due = datetime.now() + timedelta(days=3)
    params['datetime_from'] = int(mktime(datetime_from.timetuple()))
    params['datetime_due'] = int(mktime(datetime_due.utctimetuple()))
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'PUT', params)
    assert r.code == 200

    tokens = {k: params[k] for k in ('token_select', 'token_verify')}
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'GET', tokens)
    data = json.loads(r.body)
    for k in ('title', 'description', 'datetime_from', 'datetime_due'):
        assert data[k] == params[k]
    assert data['edited'] > edited

    # Invalid timestamp
    params['datetime_from'] = 'oops, this is not a timestamp'
    r = await fetch(http_client, base_url,
                    PATH['task'].format(project_id, folder_id, task_id),
                    'PUT', params)
    assert r.code == 400
