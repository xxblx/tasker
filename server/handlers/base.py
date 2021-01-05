
import nacl.exceptions
import nacl.pwhash

import tornado.web

from ..sql.select import SelectQueries


class BaseHandler(tornado.web.RequestHandler):
    @property
    def loop(self):
        return self.application.loop

    @property
    def pool_executor(self):
        return self.application.pool_executor

    @property
    def db_pool(self):
        return self.application.db_pool

    async def check_user(self, username, password):
        """ Check given username and password
        :param username: username
        :type username: str
        :param password: user's password
        :type password: str
        :return: True if user exists and password is correct,
            otherwise - False
        :rtype: bool
        """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SelectQueries.password_auth, (username,))
                _res = await cur.fetchall()
        check = False
        if _res:
            check = await self.check_password_hash(
                _res[0][0].tobytes(),
                tornado.escape.utf8(password)
            )
        return check

    async def check_password_hash(self, hashed, password):
        """ Compare entered password with exist password hash
        :param hashed: a hash of a password
        :type hashed: bytes
        :param password: a password entered by a user
        :type password: bytes
        :return: False if the password is wrong, otherwise - True
        """
        try:
            return await self.loop.run_in_executor(
                self.pool_executor,
                nacl.pwhash.verify,
                hashed,
                password
            )
        except nacl.exceptions.InvalidkeyError:
            return False
