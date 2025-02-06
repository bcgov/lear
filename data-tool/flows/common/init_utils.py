from config import get_named_config
from prefect import task
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


@task
def get_config():
    config = get_named_config()
    return config


@task
def check_db_connection(db_engine: Engine):
    with db_engine.connect() as conn:
        res = conn.execute(text('SELECT current_database()')).scalar()
        if not res:
            raise ValueError("Failed to retrieve the current database name.")
        print(f'✅ Connected to database: {res}')


@task
def colin_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for COLIN DB') from e


@task
def lear_init(config):
    try:
        engine = create_engine(
            config.SQLALCHEMY_DATABASE_URI,
            **config.SQLALCHEMY_ENGINE_OPTIONS
        )
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for LEAR DB') from e


@task
def auth_init(config):
    try:
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_AUTH)
        check_db_connection(engine)
        return engine
    except Exception as e:
        raise Exception('Failed to create engine for AUTH DB') from e
