
import json
import pytest

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
    params = await get_new_tokens(http_client, base_url, user)
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
