import asyncpg
from core.config import settings
import re

class Database:
    def __init__(self):
        self.pool_lapig = None
        self.pool_general = None

    async def connect(self):
        self.pool_lapig = await asyncpg.create_pool(
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            database=settings.PG_DATABASE_LAPIG,
            min_size=1,
            max_size=20
        )
        self.pool_general = await asyncpg.create_pool(
            user=settings.PG_USER,
            password=settings.PG_PASSWORD,
            host=settings.PG_HOST,
            port=settings.PG_PORT,
            database=settings.PG_DATABASE_GENERAL,
            min_size=1,
            max_size=20
        )

    async def disconnect(self):
        if self.pool_lapig:
            await self.pool_lapig.close()
        if self.pool_general:
            await self.pool_general.close()

    def prepare_query(self, sql_query: str, params: dict) -> str:
        for name, value in params.items():
            if isinstance(value, str):
                # Simple replacement logic matching JS version
                sql_query = sql_query.replace(f"${{{name}}}%", f"'{value.upper()}%'")
                sql_query = sql_query.replace(f"$%{{{name}}}", f"'%{value}'")
                sql_query = sql_query.replace(f"${{{name}}}", f"'{value}'")
            else:
                sql_query = sql_query.replace(f"${{{name}}}", str(value))
        return sql_query

    async def query(self, query_obj: dict, params: dict = None):
        if params is None:
            params = {}
            
        sql = self.prepare_query(query_obj['sql'], params)
        source = query_obj.get('source', 'general')

        pool = self.pool_lapig if source == 'lapig' else self.pool_general
        
        async with pool.acquire() as connection:
            rows = await connection.fetch(sql)
            return [dict(row) for row in rows]

db = Database()
