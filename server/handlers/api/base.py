
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
    _access_check = ('folder', 'task', 'project')

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

        # Check access to project and verify project, folder and task ids
        uri_list = self.request.uri.strip('/').split('/')
        uri_len = len(uri_list)
        if uri_list[1] not in self._access_check or \
                (uri_list[1] == 'project' and uri_len == 2):
            self.current_user = current_user
            return
        # project and folder and task, requested task by id
        elif uri_list[1] == 'task' and uri_len == 5:
            # user_id, project_pub_id, folder_pub_id, task_pub_id
            args = (user_id, uri_list[2], uri_list[3], uri_list[4])
            query = SelectQueries.project_folder_task_access
        # project and folder, requested list of tasks by folder
        elif uri_list[1] == 'task' and uri_len == 4:
            # user_id, project_pub_id, folder_pub_id
            args = (user_id, uri_list[2], uri_list[3])
            query = SelectQueries.project_folder_access
        # project, requested project details or list of tasks/folders
        elif uri_list[1] in self._access_check and uri_len == 3:
            # user_id, project_pub_id
            args = (user_id, uri_list[2])
            query = SelectQueries.project_access

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        if not _res:
            raise tornado.web.HTTPError(404)

        # Add project_id, folder_id, task_id, role to current_user
        # folder_id and task_id are optional, depends what users accesses
        current_user.update(dict(zip(desc, _res[0])))
        # Read-only restriction
        if self.request.method != 'GET' and current_user['role'] == 0:
            raise tornado.web.HTTPError(405)
        self.current_user = current_user
