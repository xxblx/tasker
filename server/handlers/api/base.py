
import functools

from nacl.bindings.utils import sodium_memcmp
import nacl.encoding
import nacl.hash
import tornado.escape
import tornado.web

from ..base import BaseHandler
from ...sql.select import SelectQueries


class BaseApiHandler(BaseHandler):
    @property
    def mac_key(self):
        return self.application.mac_key

    def check_xsrf_cookie(self):
        """ Don't verify _xsrf when use token-based access """
        pass

    async def hash_token(self, token, mac_key=None):
        """ Get hash of a token
        :param token: token for hashing
        :type token: str
        :param mac_key: key for message authentication
        :type mac_key: bytes
        :return: hex encoded hash of the token
        :rtype: bytes
        """
        return await self.loop.run_in_executor(
            self.pool_executor,
            # functools.partial used to pass keyword arguments to function
            functools.partial(
                # function
                nacl.hash.blake2b,
                # keyword args
                data=tornado.escape.utf8(token),
                key=mac_key,
                encoder=nacl.encoding.HexEncoder
            )
        )

    async def check_token_verify(self, plain, hashed):
        """ Check given plain-text token with a hashed one
        :param plain: verify token in plain text provided by user
        :type plain: str
        :param hashed: verify token selected from db
        :type hashed: bytes
        :return: True if hashed_token equals hash of plain_token
        :rtype: bool
        """
        _hashed = await self.hash_token(plain, self.mac_key)
        return await self.loop.run_in_executor(
            self.pool_executor, sodium_memcmp, hashed, _hashed
        )


class ApiHandler(BaseApiHandler):
    async def prepare(self):
        self.current_user = None
        try:
            token_select = self.get_argument('token_select')
            token_verify = self.get_argument('token_verify')
        except tornado.web.MissingArgumentError:
            raise tornado.web.HTTPError(403, 'invalid tokens')

        # Check tokens validity
        check_token = False
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SelectQueries.token_auth, (token_select,))
                _res = await cur.fetchall()
        if _res:
            user_id, username, token_verify_hashed = _res[0]
            token_verify_hashed = token_verify_hashed.tobytes()
            if await self.check_token_verify(token_verify, token_verify_hashed):
                check_token = True
        if not check_token:
            raise tornado.web.HTTPError(403, 'invalid tokens')

        current_user = {
            'user_id': user_id,
            # TODO: do i need username and token select here? not sure
            'username': username,
            'token_select': token_select
        }
        # Check access to the project
        uri_list = self.request.uri.strip('/').split('/')
        if uri_list[1] in ('folder', 'task', 'project') and len(uri_list) > 2:
            async with self.db_pool.acquire() as conn:
                async with conn.cursor() as cur:
                    await cur.execute(
                        SelectQueries.project_access, (user_id, uri_list[2])
                    )
                    _res = await cur.fetchall()
            if not _res:
                raise tornado.web.HTTPError(404)
            project_id, role = _res[0]
            current_user['project_id'] = project_id
            current_user['role'] = role
        self.current_user = current_user
