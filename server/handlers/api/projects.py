
from psycopg2.sql import SQL, Identifier
import tornado.web

from .base import ApiHandler
from ...sql.create import CreateSequenceQueries
from ...sql.insert import InsertQueries
from ...sql.select import SelectQueries


class ApiProjectHandler(ApiHandler):
    async def get(self):
        """ Return all projects available for a user"""
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.projects, (self.current_user['user_id'],)
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        if not _res:
            raise tornado.web.HTTPError(404)
        self.write({'projects': [dict(zip(desc, item)) for item in _res]})

    async def post(self):
        """ Create a new project """
        title = self.get_argument('title')
        description = self.get_argument('description', None)
        user_id = self.current_user['user_id']

        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                # Create project
                await cur.execute(
                    InsertQueries.add_project, (title, description)
                )
                project_id = (await cur.fetchall())[0][0]

                # Set owner
                await cur.execute(
                    InsertQueries.add_user_project, (project_id, user_id, 2)
                )

                # Create sequences for the project: folders, tasks
                seq_pf = Identifier('project_folder_{}_seq'.format(project_id))
                seq_pt = Identifier('project_task_{}_seq'.format(project_id))
                await cur.execute(
                    SQL(CreateSequenceQueries._new_sequence).format(seq=seq_pf)
                )
                await cur.execute(
                    SQL(CreateSequenceQueries._new_sequence).format(seq=seq_pt)
                )

                # Create default folder
                await cur.execute(
                    SQL(InsertQueries.add_folder).format(seq=seq_pf),
                    ('My Tasks', project_id)
                )


class ApiProjectIdHandler(ApiHandler):
    async def get(self, project_pub_id):
        """ Return detailed info about a project """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.project,
                    (self.current_user['user_id'], project_pub_id)
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        if not _res:
            raise tornado.web.HTTPError(404)
        self.write(dict(zip(desc, _res[0])))
