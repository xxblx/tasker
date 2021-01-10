
from datetime import datetime

from psycopg2.sql import SQL, Identifier, Placeholder

from .base import ApiHandler
from ...sql.delete import DeleteQueries
from ...sql.insert import InsertQueries
from ...sql.select import SelectQueries
from ...sql.update import UpdateQueries


class ApiTaskFolderHandler(ApiHandler):
    async def get(self, project_pub_id, folder_pub_id):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.tasks_by_folder,
                    (self.current_user['project_id'],
                     self.current_user['folder_id'])
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        self.write({'tasks': [dict(zip(desc, item)) for item in _res]})

    async def post(self, project_pub_id, folder_pub_id):
        args = (
            self.get_argument('title'),
            self.get_argument('description', None),
            self.get_argument('datetime_from', None),
            self.get_argument('datetime_due', None),
            self.current_user['user_id'],
            self.current_user['project_id'],
            self.current_user['folder_id']
        )
        seq_pt = Identifier(
            'project_task_{}_seq'.format(self.current_user['project_id'])
        )
        query = SQL(InsertQueries.add_task).format(seq=seq_pt)
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
                task_pub_id = (await cur.fetchall())[0][1]
        self.write({'id': task_pub_id})


class ApiTaskProjectHandler(ApiHandler):
    async def get(self, project_pub_id):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.tasks_by_project,
                    (self.current_user['project_id'],)
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        self.write({'tasks': [dict(zip(desc, item)) for item in _res]})


class ApiTaskHandler(ApiHandler):
    async def get(self, project_pub_id, folder_pub_id, task_pub_id):
        """ Get task by id """
        args = [
            self.current_user[k] for k in ('project_id', 'folder_id', 'task_id')
        ]
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(SelectQueries.task, args)
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        self.write(dict(zip(desc, _res[0])))

    async def delete(self, project_pub_id, folder_pub_id, task_pub_id):
        """ Delete a task by id """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    DeleteQueries.task, (self.current_user['task_id'],)
                )

    async def put(self, project_pub_id, folder_pub_id, task_pub_id):
        """ Update a task by id """
        args = {}
        for arg in ('title', 'description', 'datetime_from', 'datetime_due'):
            val = self.get_argument(arg, None)
            if val is None:
                continue
            if val == '' and arg != 'title':
                args[arg] = None
            # Timestamp validity check
            elif arg in ('datetime_from', 'datetime_due'):
                try:
                    args[arg] = datetime.utcfromtimestamp(int(val))
                # ValueError if value cannot be converted to int
                # OSError if value is too big for being timestamp
                except (ValueError, OSError):
                    pass
            else:
                args[arg] = val
        query = SQL(UpdateQueries.task).format(SQL(', ').join(
            [SQL('{} = {}').format(Identifier(k), Placeholder(k)) for k in args]
        ))
        args['task_id'] = self.current_user['task_id']
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(query, args)
