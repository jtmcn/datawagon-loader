import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.sql import SQL, Identifier
from typing import List, Tuple
from database_handler import DatabaseHandler


class PostgresDatabaseManager(DatabaseHandler):
    def __init__(self, db_url: str, schema: str) -> None:
        self.db_url = db_url
        self.connection_error = ""
        self.schema = schema
        try:
            self.connection = psycopg2.connect(self.db_url)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        except psycopg2.OperationalError as e:
            self.connection_error = str(e)

    # @staticmethod
    # def get_file_version(file_name: str) -> str:
    #     file_version_pattern = r"_v\d+(-\d+)?"
    #     match = re.search(file_version_pattern, file_name)
    #     if match:
    #         return match.group(0).lstrip("_")  # Remove the leading underscore
    #     else:
    #         return ""

    def test_connection(self) -> bool:
        if self.connection_error:
            print(f"Connection error: {self.connection_error}")
            return False
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("select 1")
            return True
        except psycopg2.Error:
            return False

    def check_schema(self) -> bool:
        query = SQL("select exists(select 1 from pg_namespace where nspname = %s);")

        with self.connection.cursor() as cursor:
            cursor.execute(query, (self.schema,))
            results = cursor.fetchone()

            exists = results[0] if results is not None else False

        return exists

    def get_tables_and_row_counts(self) -> List[Tuple[str, int]]:
        query = """
        select table_name, (xpath('/row/cnt/text()', xml_count))[1]::text::int as row_count
        from (
            select table_name, query_to_xml(
                'select count(*) as cnt 
                from ' || table_schema || '.' || table_name, false, true, '') as xml_count
            from information_schema.tables
            where table_schema = %s
        ) sub;
        """
        with self.connection.cursor() as cursor:
            cursor.execute(query, (self.schema,))
            tables_and_row_counts = cursor.fetchall()
        return tables_and_row_counts

    def ensure_schema_exists(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(SQL("create schema if not exists {}".format(self.schema)))

    def create_table_if_not_exists(self, table_name: str, header: List[str]) -> None:
        with self.connection.cursor() as cursor:
            columns = ", ".join([f"{col} text" for col in header])
            cursor.execute(
                SQL("create table if not exists {}.{} ({})").format(
                    Identifier(self.schema), Identifier(table_name), SQL(columns)
                )
            )

    def insert_data(
        self, table_name: str, header: List[str], data: List[List[str]]
    ) -> None:
        with self.connection.cursor() as cursor:
            placeholders = ", ".join(["%s" for _ in header])
            cursor.executemany(
                SQL("insert into {}.{} values ({})").format(
                    Identifier(self.schema), Identifier(table_name), SQL(placeholders)
                ),
                data,
            )

    def close(self) -> None:
        self.connection.close()


    def drop_all_tables_and_views(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f"""
                DO $$ DECLARE
                    r RECORD;
                BEGIN
                    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = '{self.schema}')
                    LOOP
                        EXECUTE 'DROP TABLE IF EXISTS {self.schema}.' || r.tablename || ' CASCADE';
                    END LOOP;
                    FOR r IN (SELECT viewname FROM pg_views WHERE schemaname = '{self.schema}')
                    LOOP
                        EXECUTE 'DROP VIEW IF EXISTS {self.schema}.' || r.viewname || ' CASCADE';
                    END LOOP;
                END $$;
                """
            )