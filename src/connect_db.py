import psycopg2

from config import DatabaseConfig


def test_db_connection():
    """ Connect to the PostgreSQL database server """
    try:
        # connecting to the PostgreSQL server
        database_config = DatabaseConfig()
        with psycopg2.connect(
            host=database_config.host,
            port=database_config.port,
            user=database_config.user,
            password=database_config.password.get_secret_value(),
            database=database_config.database,
        ) as conn:
            print('Connected to the PostgreSQL server.')
            return conn
    except (psycopg2.DatabaseError, Exception) as error:
        print(error)
