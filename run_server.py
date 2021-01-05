#!/usr/bin/env python3

import tornado.httpserver
import tornado.ioloop

from server.conf import HOST, PORT
from server.app import ServerApp, get_db_pool


def main():
    loop = tornado.ioloop.IOLoop.current()
    db_pool = loop.asyncio_loop.run_until_complete(get_db_pool())
    app = ServerApp(loop.asyncio_loop, db_pool)
    http_server = tornado.httpserver.HTTPServer(app)
    http_server.listen(PORT, HOST)

    try:
        loop.start()
    except KeyboardInterrupt:
        app.db_pool.close()
        loop.asyncio_loop.run_until_complete(app.db_pool.wait_closed())
        loop.stop()
    finally:
        loop.close()


if __name__ == '__main__':
    main()
