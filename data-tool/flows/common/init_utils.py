from config import get_named_config
from prefect import task
from prefect.cache_policies import NO_CACHE
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import oracledb


@task(cache_policy=NO_CACHE)
def get_config():
    config = get_named_config()
    return config


@task(cache_policy=NO_CACHE)
def check_postgres_connection(db_engine: Engine):
    """Postgres DB Connection Check."""
    with db_engine.connect() as conn:
        res = conn.execute(text('SELECT current_database()')).scalar()
        if not res:
            raise ValueError("Failed to retrieve the current database name.")
        print(f'✅ Connected to Postgres database: {res}')


@task(cache_policy=NO_CACHE)
def colin_extract_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
        check_postgres_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for COLIN Extract DB') from e


@task(cache_policy=NO_CACHE)
def colin_oracle_init(config):
    try:
        # Make sure instant client is installed and thick mode is enabled
        oracledb.init_oracle_client()
        print('👷 Enable thick mode:', not oracledb.is_thin_mode())
        print('👷 Instant Client version:', oracledb.clientversion())
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_ORACLE)
        # Check oracle connection
        with engine.connect() as conn:
            res = conn.execute(
                text("""SELECT SYS_CONTEXT('USERENV', 'DB_NAME') FROM DUAL""")
            ).scalar()
            if not res:
                raise ValueError("Failed to retrieve the current database name.")
            print(f'✅ Connected to Oracle database: {res}')
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for COLIN Oracle DB') from e

@task(cache_policy=NO_CACHE)
def lear_init(config):
    try:
        engine = create_engine(
            config.SQLALCHEMY_DATABASE_URI,
            **config.SQLALCHEMY_ENGINE_OPTIONS
        )
        check_postgres_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for LEAR DB') from e


@task(cache_policy=NO_CACHE)
def auth_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_AUTH)
        check_postgres_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for AUTH DB') from e
