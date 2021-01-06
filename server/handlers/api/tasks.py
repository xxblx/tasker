
from psycopg2.sql import SQL, Identifier

from .base import ApiHandler
from ...sql.insert import InsertQueries
from ...sql.select import SelectQueries


class ApiTaskFolderHandler(ApiHandler):
    async def get(self, project_pub_id, folder_pub_id):
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.tasks_by_folder,
                    (self.current_user['project_id'], folder_pub_id)
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        self.write({'folders': [dict(zip(desc, item)) for item in _res]})

    # async def post(self, project_pub_id, folder_pub_id):
    #     title = self.get_argument('title')
    #     description = self.get_argument('description', None)
    #     datetime_from = self.get_argument('datetime_from', None)
    #     datetime_due = self.get_argument('datetime_due', None)
    #     user_id = self.current_user['user_id']
    #     project_id = self.current_user['project_id']
