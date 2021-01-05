
from concurrent.futures import ThreadPoolExecutor

import aiopg
import nacl.utils
import tornado.web

from .conf import DEBUG, TOKEN_EXPIRES_TIME, WORKERS, DB_SETTINGS
from .handlers.api.tokens import GetTokensHandler, RenewTokensHandler
from .handlers.api.projects import ApiProjectHandler, ApiProjectIdHandler
from .handlers.api.folders import ApiFolderHandler, ApiFolderIdHandler


class ServerApp(tornado.web.Application):
    def __init__(self, loop, db_pool):
        self.loop = loop
        self.db_pool = db_pool
        self.mac_key = nacl.utils.random(size=64)
        self.token_expires_time = TOKEN_EXPIRES_TIME
        self.pool_executor = ThreadPoolExecutor(max_workers=WORKERS)

        handlers = [
            (r'/api/tokens/get', GetTokensHandler),
            (r'/api/tokens/renew', RenewTokensHandler),

            (r'/api/project', ApiProjectHandler),
            (r'/api/project/([0-9]*/?)', ApiProjectIdHandler),

            (r'/api/folder/([0-9]*/?)', ApiFolderHandler),
            (r'/api/folder/([0-9]*)/([0-9]*/?)', ApiFolderIdHandler),

            (r'/api/task/([0-9]*)/([0-9]*/?)', None),
            (r'/api/task/([0-9]*)/([0-9]*)/([0-9]*/?)', None)
        ]
        #template_path = os.path.join(os.path.dirname(__file__), 'templates')
        #static_path = os.path.join(os.path.dirname(__file__), 'static')
        settings = {
            #'template_path': template_path,
            #'static_path': static_path,
            'debug': DEBUG,
            'xsrf_cookies': True,
            'cookie_secret': nacl.utils.random(size=64)
        }

        super().__init__(handlers, **settings)


async def get_db_pool():
    return await aiopg.create_pool(**DB_SETTINGS)