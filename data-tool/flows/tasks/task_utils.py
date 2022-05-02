from flask_sqlalchemy import SQLAlchemy
from prefect import Task
from sqlalchemy import create_engine


class LearInitTask(Task):

    def __init__(self, flask_app_name, **kwargs):
        self.flask_app_name = flask_app_name
        super().__init__(**kwargs)

    def run(self, config):
        from legal_api.models import db
        from flask import Flask
        FLASK_APP = Flask(self.flask_app_name)
        FLASK_APP.config.from_object(config)
        db.init_app(FLASK_APP)
        FLASK_APP.app_context().push()
        return FLASK_APP, db


class ColinInitTask(Task):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def run(self, config):
        engine = create_engine(config.SQLALCHEMY_DATABASE_URI_COLIN_MIGR)
        return engine


