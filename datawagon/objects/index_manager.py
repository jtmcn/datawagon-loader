import pandas as pd
from psycopg2.sql import SQL, Identifier

from datawagon.objects.database_manager import DatabaseManager


class IndexManager:
    """
    Create/drop indexes on all tables and check the size of all indexes in the schema.

    6/20/23 - Indexes may not be useful to end user and this class is not used in the main code.
    """

    def __init__(self, db_manager: DatabaseManager) -> None:
        self.db_manager = db_manager

    def create_index_on_all_tables(self) -> None:
        with self.db_manager.connection.cursor() as cursor:
            for table_name in self.db_manager.table_names():
                index_name = f"{table_name}_{self.db_manager.INDEX_COLUMN_NAME}_idx"
                index_query = SQL("create index if not exists {} on {}.{}({});").format(
                    Identifier(index_name),
                    Identifier(self.db_manager.schema),
                    Identifier(table_name),
                    Identifier(self.db_manager.INDEX_COLUMN_NAME),
                )
                print(index_query)
                cursor.execute(index_query)
            cursor.close()

    def drop_index_on_all_tables(self) -> None:
        with self.db_manager.connection.cursor() as cursor:
            for table_name in self.db_manager.table_names():
                index_name = f"{table_name}_{self.db_manager.INDEX_COLUMN_NAME}_idx"
                query = SQL("drop index if exists {}.{};").format(
                    Identifier(self.db_manager.schema), Identifier(index_name)
                )
                cursor.execute(query)
            cursor.close()

    def get_all_indexes(self) -> pd.DataFrame:
        """
        Returns a DataFrame containing the table name, index name and size of all indexes in the schema.
        """

        query = f"""
        select
            t.relname as table_name,
            i.relname as index_name,
            pg_size_pretty(pg_relation_size(i.oid)) as size
        from
            pg_class t,
            pg_class i,
            pg_index ix,
            pg_namespace n
        where
            t.oid = ix.indrelid
            and i.oid = ix.indexrelid
            and t.relkind = 'r'
            and t.relnamespace = n.oid
            and n.nspname = '{self.db_manager.schema}'
        """
        df = pd.read_sql_query(query, self.db_manager.engine)
        return df
