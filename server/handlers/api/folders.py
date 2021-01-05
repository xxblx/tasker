
from psycopg2.sql import SQL, Identifier

from .base import ApiHandler
from ...sql.insert import InsertQueries
from ...sql.select import SelectQueries


class ApiFolderHandler(ApiHandler):
    async def get(self, project_pub_id):
        """ Return all folders in a project """
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SelectQueries.folders, (self.current_user['project_id'],)
                )
                _res = await cur.fetchall()
                desc = [item.name for item in cur.description]
        self.write({'folders': [dict(zip(desc, item)) for item in _res]})

    async def post(self, project_pub_id):
        """ Create a new folder """
        title = self.get_argument('title')
        project_id = self.current_user['project_id']
        seq_pf = Identifier('project_folder_{}_seq'.format(project_id))
        async with self.db_pool.acquire() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    SQL(InsertQueries.add_folder).format(seq=seq_pf),
                    (title, project_id)
                )
