
import json
import pytest
from uuid import uuid4

from .base import PATH, app, user, fetch
from db_manage import delete_user


@pytest.mark.gen_test
async def test_tokens_new(http_client, base_url, user):
    _user = user['password_auth']
    # Valid username and password
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', _user)
    assert r.code == 200

    # Valid username and invalid password
    password = _user['password']
    _user['password'] = uuid4().hex
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', _user)
    assert r.code == 403

    # Delete user and try to get new tokens again
    # Invalid username and invalid password
    _user['password'] = password
    delete_user(_user['username'])
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST', _user)
    assert r.code == 403


@pytest.mark.gen_test
async def test_tokens_renew(http_client, base_url, user):
    r = await fetch(http_client, base_url, PATH['new_tokens'], 'POST',
                    user['password_auth'])
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
