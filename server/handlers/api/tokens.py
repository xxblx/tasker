
from datetime import datetime, timedelta
from time import mktime
from uuid import uuid4

from psycopg2.sql import SQL, Identifier
import tornado.web

from .base import BaseApiHandler
from ...sql.delete import DeleteQueries
from ...sql.insert import InsertQueries
from ...sql.select import SelectQueries


class BaseTokensHandler(BaseApiHandler):
    @property
    def token_expires_time(self):
        return self.application.token_expires_time

    async def generate_tokens(self, username):
        """ Generate three new tokens for a user with given username:
            * select_token used in select queries in db.
            * verify_token used for verification of select and renew tokens.
                verify_token isn't stored directly in db. Instead of that
                hash of the token stored. In case of unexpected read access
                to db (e.g. theft of db dump, injection, etc) plain
                verify_token isn't going to be compromised, it makes
                all stolen tokens useless because only the app knows mac key
                used for hashing and the app always hashes the content of
                the verify_token argument of post request.
            * renew_token used for one-time issuing new three tokens.
        :return: a dict with tokens
        """
        token_select = uuid4().hex
        token_verify = uuid4().hex
        token_renew = uuid4().hex
        # verify_token stored as a hash instead of plain-text
        token_verify_hash = await self.hash_token(token_verify, self.mac_key)
        # Formatted query has expression like
        # `CURRENT_TIMESTAMP + '7200s'::INTERVAL`
        # where 7200 is `TOKEN_EXPIRES_TIME` defined in `conf.py`
        query = SQL(InsertQueries.tokens).format(
            Identifier('{}s'.format(self.token_expires_time))
        )
        args = (token_select, token_verify_hash, token_renew, username)
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                _res = await cur.fetchall()
        tokens = {
            'token_select': token_select,
            'token_verify': token_verify,
            'token_renew': token_renew,
            'expires_in': _res[0][0]
        }
        return tokens


class ApiTokensNewHandler(BaseTokensHandler):
    async def post(self):
        try:
            username = self.get_argument('username')
            password = self.get_argument('password')
        except tornado.web.MissingArgumentError:
            raise tornado.web.HTTPError(400)

        check = await self.check_user(username, password)
        if not check:
            raise tornado.web.HTTPError(403, 'invalid username or password')

        tokens = await self.generate_tokens(username)
        self.write(tokens)


class ApiTokensRenewHandler(BaseTokensHandler):
    async def post(self):
        try:
            token_select = self.get_argument('token_select')
            token_verify = self.get_argument('token_verify')
            token_renew = self.get_argument('token_renew')
        except tornado.web.MissingArgumentError:
            raise tornado.web.HTTPError(403, 'invalid tokens')

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.token_renew,
                    (token_select, token_renew)
                )
                _res = await cur.fetchall()

        if not _res:
            raise tornado.web.HTTPError(403, 'invalid tokens')

        username, token_verify_hashed, token_id = _res[0]
        token_verify_hashed = token_verify_hashed.tobytes()
        # Compare hashes
        check = await self.check_token_verify(token_verify, token_verify_hashed)
        if not check:
            raise tornado.web.HTTPError(403, 'invalid tokens')

        # Delete used tokens
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(DeleteQueries.delete_tokens, (token_id,))
        # Generate new set
        tokens = await self.generate_tokens(username)
        self.write(tokens)
