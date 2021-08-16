import os
import yaml
import psycopg2
import pandas as pd
from sqlalchemy import create_engine
from typing import Union, Iterable
from pathlib import Path
from fantasy_football.mailer import send_info


def _load_yaml(_path: str) -> dict:
    """Loads yaml content
    """
    _yaml_file = open(_path, 'r', encoding='utf8')
    _yaml_content = yaml.safe_load(_yaml_file)
    _yaml_file.close()
    return _yaml_content


def get_credentials() -> dict:
    """Loads the credential file with all config stored in ./private/creds.yaml

    :return: Credentials in a dictionary form
    """
    credentials_path = Path(os.path.abspath(__file__)).parent.parent / "private" / "creds.yaml"
    return _load_yaml(credentials_path)


def _get_connection() -> None:
    """A helper to get the connection to the fpl db

    :return: Psycopg2 connection object with predefined credentials
    """
    creds = get_credentials()['server']
    connection = psycopg2.connect(
        host=creds['host'],
        port=creds['port'],
        database=creds['database'],
        user=creds['username'],
        password=creds['password'])
    return connection


def get_query(query: str) -> pd.DataFrame:
    """Makes query to the database and returns the output

    :param query: SQL query
    :type query: str
    :return: Output of the SQL query
    """
    connection = _get_connection()
    cur = connection.cursor()
    cur.execute(query)
    columns = [desc[0] for desc in cur.description]
    data = cur.fetchall()
    cur.close()
    connection.close()
    return pd.DataFrame(columns=columns, data=data)


def execute_query(queries: Union[str, Iterable[str]]) -> None:
    """A helper to execute provded SQL query

    :param queries: Query, or a set of queries to execute
    :type queries: Union[str, Iterable[str]]
    """
    if isinstance(queries, str):
        queries = [queries]
    _connection = _get_connection()
    _cursor = _connection.cursor()
    for query in queries:
        _cursor.execute(query)
    _connection.commit()
    _cursor.close()
    _connection.close()


def insert_dataframe(input_df: pd.DataFrame, _table_name: str = "players") -> None:
    """Helps to save given dataframe into the database

    :param input_df: Input dataframe
    :type input_df: pd.DataFrame
    """
    creds = get_credentials()['server']
    _engine = create_engine(
        f"postgresql://{creds['username']}:{creds['password']}@{creds['host']}:{creds['port']}/{creds['database']}")
    input_df.to_sql(_table_name, _engine, if_exists='append', index=False)
    send_info(subject=f"{_table_name.capitalize()} table updated", message_content=f"Updated with {len(input_df)} rows")